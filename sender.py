
import socket
import time
import random
import sys
import os
from datetime import datetime

class ALOHASender:
    def __init__(self, sender_id, file_path, target_ips, port=5005):
        self.sender_id = sender_id.zfill(4)[:4]
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.target_ips = target_ips
        self.port = port
        self.chunk_size = 1024
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def send_file(self, min_delay=0.1, max_delay=3.0):
        print(f"[{self.sender_id}] ALOHA Sender starting...")
        print(f"[{self.sender_id}] File: {self.filename}")
        print(f"[{self.sender_id}] Targets: {self.target_ips}")
        print(f"[{self.sender_id}] Backoff range: {min_delay}s - {max_delay}s")
        print("-" * 50)
        
        # Read and chunk file
        with open(self.file_path, "rb") as f:
            data = f.read()
            
        chunks = [data[i:i+self.chunk_size] for i in range(0, len(data), self.chunk_size)]
        total_chunks = len(chunks)
        
        print(f"[{self.sender_id}] File size: {len(data)} bytes, {total_chunks} chunks")
        
        for chunk_no, chunk in enumerate(chunks):
            # Pure ALOHA: Random backoff before each transmission
            backoff = random.uniform(min_delay, max_delay)
            time.sleep(backoff)
            
            # Create packet header
            filename_bytes = self.filename.encode()
            header = (
                self.sender_id.encode() +              # 4 bytes: sender ID
                chunk_no.to_bytes(4, "big") +          # 4 bytes: chunk number
                total_chunks.to_bytes(4, "big") +      # 4 bytes: total chunks
                len(filename_bytes).to_bytes(2, "big") + # 2 bytes: filename length
                filename_bytes                          # variable: filename
            )
            
            packet = header + chunk
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            
            # Broadcast to all receivers
            for ip in self.target_ips:
                try:
                    self.sock.sendto(packet, (ip, self.port))
                except Exception as e:
                    print(f"[{timestamp}] ERROR sending to {ip}: {e}")
                    
            print(f"[{timestamp}] TX chunk {chunk_no+1}/{total_chunks} (backoff: {backoff:.3f}s)")
            
        print(f"[{self.sender_id}] ✓ Transmission complete!")
        self.sock.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python aloha_sender.py <sender_id> <file_path>")
        sys.exit(1)
        
    sender_id = sys.argv[1]
    file_path = sys.argv[2]
    
    # Target all devices in demonstration network
    target_ips = [
           # Host laptop
        "192.168.137.211"  # Laptop 2
    ]
    
    sender = ALOHASender(sender_id, file_path, target_ips)
    sender.send_file()
