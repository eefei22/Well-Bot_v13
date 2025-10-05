#!/usr/bin/env python3
"""
Deepgram TTS Integration Test Script
Tests the complete Deepgram TTS pipeline from server startup to audio generation.
"""

import os
import sys
import time
import json
import subprocess
import requests
import asyncio
import websockets
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class DeepgramTester:
    """Comprehensive Deepgram TTS integration tester."""
    
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts
        self.server_url = "http://localhost:8080"
        self.tts_endpoint = f"{self.server_url}/speech/tts:test"
        self.health_endpoint = f"{self.server_url}/healthz"
        self.ready_endpoint = f"{self.server_url}/readyz"
        # Determine project root - look for src/backend/api/main.py
        current_dir = Path.cwd()
        if (current_dir / "src" / "backend" / "api" / "main.py").exists():
            # We're in project root
            self.project_root = current_dir
        elif (current_dir.parent / "src" / "backend" / "api" / "main.py").exists():
            # We're in tests/ directory
            self.project_root = current_dir.parent
        else:
            # Try to find project root by looking for src/backend/api/main.py
            self.project_root = None
            for parent in current_dir.parents:
                if (parent / "src" / "backend" / "api" / "main.py").exists():
                    self.project_root = parent
                    break
        
        if self.project_root is None:
            raise RuntimeError("Could not find project root directory")
        
        self.server_dir = self.project_root / "src" / "backend" / "api"
        self.test_output_dir = self.project_root / "tests" / "output"
        self.log_file = self.test_output_dir / "tts.log"
        self.server_process: Optional[subprocess.Popen] = None
        
        # Create test output directory
        self.test_output_dir.mkdir(exist_ok=True)
        
        # Initialize log file
        self.log(f"Starting Deepgram TTS Integration Test")
        self.log(f"Max attempts: {max_attempts}")
        self.log(f"Server URL: {self.server_url}")
    
    def log(self, message: str) -> None:
        """Log message to console and file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        self.log("Checking prerequisites...")
        
        # Check if we found the project structure
        if not (self.server_dir / "main.py").exists():
            self.log("[FAILED] Error: Could not find project structure")
            self.log(f"Looking for: {self.server_dir / 'main.py'}")
            self.log(f"Current directory: {Path.cwd()}")
            self.log(f"Project root: {self.project_root}")
            return False
        
        self.log(f"[PASSED] Found project root: {self.project_root}")
        
        # Check if Python is available
        try:
            subprocess.run([sys.executable, "--version"], 
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("[FAILED] Error: Python not found")
            return False
        
        # Check if requests is available
        try:
            import requests
        except ImportError:
            self.log("[FAILED] Error: requests library not found")
            self.log("Install with: pip install requests")
            return False
        
        self.log("[PASSED] Prerequisites check passed")
        return True
    
    def check_server_running(self) -> bool:
        """Check if server is running."""
        try:
            response = requests.get(self.health_endpoint, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def start_server(self) -> bool:
        """Start the FastAPI server."""
        self.log("Starting FastAPI server...")
        
        try:
            # Change to server directory and start server
            self.server_process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=self.server_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for server to start
            self.log("Waiting for server to start...")
            for i in range(15):  # Wait up to 30 seconds
                time.sleep(2)
                if self.check_server_running():
                    self.log("[PASSED] Server started successfully")
                    return True
            
            self.log("[FAILED] Server failed to start within 30 seconds")
            return False
            
        except Exception as e:
            self.log(f"[FAILED] Error starting server: {e}")
            return False
    
    def test_health_endpoints(self) -> bool:
        """Test health endpoints."""
        self.log("Testing health endpoints...")
        
        try:
            # Test /healthz
            self.log("Testing /healthz endpoint...")
            response = requests.get(self.health_endpoint, timeout=10)
            if response.status_code != 200:
                self.log("[FAILED] /healthz endpoint failed")
                return False
            self.log("[PASSED] /healthz endpoint working")
            
            # Test /readyz
            self.log("Testing /readyz endpoint...")
            response = requests.get(self.ready_endpoint, timeout=10)
            if response.status_code != 200:
                self.log("[FAILED] /readyz endpoint failed")
                return False
            self.log("[PASSED] /readyz endpoint working")
            
            # Get detailed readiness status
            self.log("Checking detailed readiness status...")
            response = requests.get(self.ready_endpoint, timeout=10)
            readiness_data = response.json()
            
            # Save readiness data
            with open(self.test_output_dir / "health.json", "w") as f:
                json.dump(readiness_data, f, indent=2)
            
            # Check if Deepgram is configured
            if "deepgram" not in readiness_data:
                self.log("[FAILED] Deepgram not found in readiness check")
                return False
            
            deepgram_status = readiness_data["deepgram"]
            if deepgram_status.get("status") != "ok":
                self.log(f"[FAILED] Deepgram status: {deepgram_status}")
                return False
            
            self.log("[PASSED] Deepgram configuration found and healthy")
            return True
            
        except Exception as e:
            self.log(f"[FAILED] Error testing health endpoints: {e}")
            return False
    
    def test_tts_endpoint(self) -> bool:
        """Test TTS endpoint."""
        self.log("Testing TTS endpoint...")
        
        try:
            # Test with default text
            self.log("Testing TTS with default text...")
            response = requests.post(self.tts_endpoint, timeout=30)
            if response.status_code != 200:
                self.log(f"[FAILED] TTS endpoint failed: {response.status_code}")
                return False
            
            # Save default audio
            default_audio_path = self.test_output_dir / "tts_default.mp3"
            with open(default_audio_path, "wb") as f:
                f.write(response.content)
            
            if len(response.content) == 0:
                self.log("[FAILED] Generated audio file is empty")
                return False
            
            self.log(f"[PASSED] TTS endpoint working - Generated {len(response.content)} bytes of audio")
            
            # Test with custom text
            self.log("Testing TTS with custom text...")
            custom_text = "Testing Well-Bot TTS integration"
            response = requests.post(
                self.tts_endpoint,
                json={"text": custom_text},
                timeout=30
            )
            
            if response.status_code != 200:
                self.log(f"[FAILED] TTS endpoint failed with custom text: {response.status_code}")
                return False
            
            # Save custom audio
            custom_audio_path = self.test_output_dir / "tts_custom.mp3"
            with open(custom_audio_path, "wb") as f:
                f.write(response.content)
            
            if len(response.content) == 0:
                self.log("[FAILED] Generated custom audio file is empty")
                return False
            
            self.log(f"[PASSED] Custom TTS working - Generated {len(response.content)} bytes of audio")
            return True
            
        except Exception as e:
            self.log(f"[FAILED] Error testing TTS endpoint: {e}")
            return False
    
    def test_audio_validity(self) -> bool:
        """Test audio file validity."""
        self.log("Validating generated audio files...")
        
        try:
            # Check MP3 headers
            self.log("Checking MP3 file headers...")
            
            for audio_file in ["tts_default.mp3", "tts_custom.mp3"]:
                audio_path = self.test_output_dir / audio_file
                
                if not audio_path.exists():
                    self.log(f"[FAILED] Audio file not found: {audio_file}")
                    return False
                
                # Check MP3 header (ID3 or MPEG)
                with open(audio_path, "rb") as f:
                    header = f.read(10)
                
                # Check for MP3 sync word (0xFF 0xFB/0xFA) or ID3 tag
                is_valid = (
                    (header[0] == 0xFF and (header[1] & 0xE0) == 0xE0) or  # MPEG header
                    (header[:3] == b'ID3')  # ID3 tag
                )
                
                if not is_valid:
                    self.log(f"[FAILED] {audio_file} has invalid MP3 header")
                    return False
                
                self.log(f"[PASSED] {audio_file} has valid MP3 header")
            
            return True
            
        except Exception as e:
            self.log(f"[FAILED] Error validating audio files: {e}")
            return False
    
    def generate_report(self) -> None:
        """Generate test report."""
        self.log("Generating test report...")
        
        report_path = self.test_output_dir / "tts_report.txt"
        
        # Get file sizes
        default_size = (self.test_output_dir / "tts_default.mp3").stat().st_size
        custom_size = (self.test_output_dir / "tts_custom.mp3").stat().st_size
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("Well-Bot Deepgram TTS Integration Test Report\n")
            f.write("================================================\n")
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Test Status: PASSED\n\n")
            f.write("Test Results:\n")
            f.write("- Server startup: [PASSED]\n")
            f.write("- Health endpoints: [PASSED]\n")
            f.write("- TTS endpoint: [PASSED]\n")
            f.write("- Audio generation: [PASSED]\n")
            f.write("- Audio validation: [PASSED]\n\n")
            f.write("Generated Files:\n")
            f.write(f"- tts_default.mp3 ({default_size} bytes)\n")
            f.write(f"- tts_custom.mp3 ({custom_size} bytes)\n")
            f.write("- readiness.json\n")
            f.write("- test_deepgram.log\n\n")
            f.write("You can play the generated MP3 files to verify TTS quality.\n")
        
        self.log(f"[PASSED] Test report generated: {report_path}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.log("Cleaning up...")
        
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            except Exception as e:
                self.log(f"Warning: Error stopping server: {e}")
        
        self.log("[PASSED] Cleanup completed")
    
    def run_test(self) -> bool:
        """Run the complete test suite."""
        try:
            # Check prerequisites
            if not self.check_prerequisites():
                return False
            
            # Run tests with retry logic
            for attempt in range(1, self.max_attempts + 1):
                self.log(f"=== ATTEMPT {attempt} of {self.max_attempts} ===")
                
                try:
                    # Start server
                    if not self.start_server():
                        continue
                    
                    # Test health endpoints
                    if not self.test_health_endpoints():
                        continue
                    
                    # Test TTS endpoint
                    if not self.test_tts_endpoint():
                        continue
                    
                    # Test audio validity
                    if not self.test_audio_validity():
                        continue
                    
                    # All tests passed
                    self.log("[PASSED] ALL TESTS PASSED!")
                    self.generate_report()
                    return True
                    
                except Exception as e:
                    self.log(f"[FAILED] Attempt {attempt} failed: {e}")
                    self.cleanup()
                    
                    if attempt < self.max_attempts:
                        self.log("Retrying in 5 seconds...")
                        time.sleep(5)
            
            # All attempts failed
            self.log(f"[FAILED] All {self.max_attempts} attempts failed")
            return False
            
        finally:
            self.cleanup()


def main():
    """Main entry point."""
    print("=" * 50)
    print("Well-Bot Deepgram TTS Integration Test")
    print("=" * 50)
    print()
    
    tester = DeepgramTester(max_attempts=3)
    
    try:
        success = tester.run_test()
        
        if success:
            print()
            print("=" * 50)
            print("Test completed successfully!")
            print("Check tests/output/ for results")
            print("=" * 50)
            sys.exit(0)
        else:
            print()
            print("=" * 50)
            print("Test failed!")
            print("Check tests/output/tts.log for details")
            print("=" * 50)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        tester.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        tester.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
