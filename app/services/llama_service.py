from typing import List, Dict, Optional
import aiohttp
import logging
import time
import json
import os
import re
from .monitoring_service import MonitoringService

class LlamaService:
    def __init__(self, monitoring_service: MonitoringService):
        # Get host configuration from environment or use default
        self.host = os.getenv("LLAMA_HOST", "host.docker.internal")
        self.port = int(os.getenv("LLAMA_PORT", "11434"))
        self.base_url = f"http://{self.host}:{self.port}/v1/completions"
        self.model = "phi4:latest"
        self.monitoring = monitoring_service
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing LlamaService with URL: {self.base_url}")

    def _extract_response_text(self, response_data: dict) -> Optional[str]:
        """Extract response text from Ollama response format"""
        try:
            # Get first choice's text
            if response_data.get("choices") and len(response_data["choices"]) > 0:
                return response_data["choices"][0]["text"]
            return None
        except Exception as e:
            self.logger.error(f"Error extracting response text: {e}")
            return None

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using simple regex"""
        # Split on period followed by space or newline, exclamation mark, or question mark
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]

    async def _call_llm(self, prompt: str, operation: str) -> Optional[str]:
        """Make a call to the local Llama instance"""
        start_time = time.time()
        self.logger.debug(f"Starting LLM call for operation: {operation}")
        
        try:
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            self.logger.debug(f"Request data: {json.dumps(request_data)}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=request_data,
                    timeout=30
                ) as response:
                    response_time = time.time() - start_time
                    self.logger.debug(f"Response status: {response.status}")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Llama API error: {response.status}, Response: {error_text}")
                        self.monitoring.record_llama_metrics(
                            operation=operation,
                            response_time=response_time,
                            success=False
                        )
                        return None
                    
                    raw_response = await response.text()
                    self.logger.debug(f"Raw response: {raw_response}")
                    
                    try:
                        result = json.loads(raw_response)
                        self.logger.debug(f"Parsed response: {json.dumps(result, indent=2)}")
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse JSON response: {e}")
                        return None
                    
                    response_text = self._extract_response_text(result)
                    if response_text:
                        self.logger.debug(f"Extracted response text: {response_text[:200]}...")
                        self.monitoring.record_llama_metrics(
                            operation=operation,
                            response_time=response_time,
                            success=True,
                            quality_score=1.0
                        )
                        return response_text
                    else:
                        self.logger.error("No response text found in result")
                        return None

        except Exception as e:
            self.logger.error(f"Error calling Llama: {str(e)}", exc_info=True)
            self.monitoring.record_llama_metrics(
                operation=operation,
                response_time=time.time() - start_time,
                success=False
            )
            return None

    async def health_check(self) -> Optional[str]:
        """Test connection to Llama service"""
        operation = "health_check"
        prompt = "Say 'connected' if you can read this."
        
        response = await self._call_llm(prompt, operation)
        if response and "connect" in response.lower():
            return response
        return None

    async def generate_stops(self, city: str, theme: str, language: str = "en-us") -> List[Dict[str, str]]:
        """Generate initial set of stops based on location and theme"""
        operation = "generate_stops"
        self.logger.info(f"Generating stops for {city}, theme: {theme}, language: {language}")
        
        prompt = f"""Generate a list of 15 interesting {theme} stops in {city}. 
        Focus only on {theme} aspects.
        Return a simple list with one location name per line."""

        response = await self._call_llm(prompt, operation)
        if not response:
            self.logger.error("Failed to generate stops - no response from LLM")
            return []

        # Parse stops from response
        stops = []
        try:
            # Log raw response
            self.logger.debug(f"Raw stops response:\n{response}")
            
            # Split response into lines and clean up
            lines = [line.strip() for line in response.split('\n')]
            self.logger.debug(f"Split into {len(lines)} lines: {lines}")
            
            # Process each line
            for line in lines:
                # Remove numbering and common list markers
                line = line.strip()
                if not line:
                    continue
                    
                # Remove numbering (e.g., "1.", "2.")
                if '. ' in line:
                    parts = line.split('. ', 1)
                    if parts[0].isdigit():
                        line = parts[1]
                
                # Remove other markers
                line = line.lstrip('.-*# ')
                
                if line:  # If we still have text after cleaning
                    self.logger.debug(f"Adding stop: {line}")
                    stops.append({"name": line})

            self.logger.info(f"Successfully generated {len(stops)} stops")
            self.logger.debug(f"Final stops list: {json.dumps(stops, indent=2)}")

            self.monitoring.record_llama_metrics(
                operation=operation,
                response_time=0,
                success=True,
                quality_score=len(stops) / 15.0
            )

            return stops[:15]
        except Exception as e:
            self.logger.error(f"Error parsing stops response: {str(e)}", exc_info=True)
            self.logger.error(f"Response was: {response}")
            return []

    async def generate_description(
        self,
        stop_name: str,
        theme: str,
        language: str = "en-us"
    ) -> Optional[str]:
        """Generate themed description for a specific stop"""
        operation = "generate_description"
        self.logger.info(f"Generating description for {stop_name}, theme: {theme}, language: {language}")
        
        prompt = f"""Provide a {theme}-focused description of {stop_name}.
        Focus strictly on {theme} aspects.
        Keep it engaging and informative.
        Maximum length: 3-4 sentences."""

        description = await self._call_llm(prompt, operation)
        if not description:
            self.logger.error(f"Failed to generate description for {stop_name}")
            return None

        try:
            # Clean up description
            description = description.strip()
            
            # Split into sentences
            sentences = self._split_into_sentences(description)
            self.logger.debug(f"Split into {len(sentences)} sentences")
            
            # Apply length constraints
            result = ""
            for sentence in sentences:
                if len(result) + len(sentence) + 1 > 500:  # +1 for space
                    break
                if result:
                    result += " "
                result += sentence

            if result:
                self.monitoring.record_llama_metrics(
                    operation=operation,
                    response_time=0,
                    success=True,
                    quality_score=min(1.0, len(result) / 500.0)
                )
                return result
            return None

        except Exception as e:
            self.logger.error(f"Error processing description: {str(e)}", exc_info=True)
            return None