
import socket
import os
import time
import threading
from datetime import datetime

class ALOHAReceiver:
    def __init__(self, port=5005, device_id="RECV"):
        self.port = port
        self.device_id = device_id
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", port))
        self.active_transfers = {}
        self.stats = {"received": 0, "collisions": 0, "completed": 0}
        
    def start_listening(self):
        print(f"[{self.device_id}] ALOHA Receiver listening on UDP port {self.port}")
        print(f"[{self.device_id}] Started at: {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 50)
        
        while True:
            try:
                data, addr = self.sock.recvfrom(8192)
                self.process_packet(data, addr)
            except KeyboardInterrupt:
                print(f"\n[{self.device_id}] Shutting down...")
                break
                
    def process_packet(self, data, addr):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        try:
            # Parse header: sender_id(4) + chunk_no(4) + total_chunks(4) + filename_len(2)
            sender_id = data[:4].decode()
            chunk_no = int.from_bytes(data[4:8], "big")
            total_chunks = int.from_bytes(data[8:12], "big")
            filename_len = int.from_bytes(data[12:14], "big")
            filename = data[14:14+filename_len].decode()
            payload = data[14+filename_len:]
            
            # Track transfer progress
            transfer_key = f"{sender_id}_{filename}"
            
            if transfer_key not in self.active_transfers:
                self.active_transfers[transfer_key] = {
                    "chunks": {},
                    "total": total_chunks,
                    "filename": filename,
                    "sender": sender_id,
                    "start_time": time.time()
                }
                os.makedirs(f"received_{self.device_id}", exist_ok=True)
                
            # Store chunk
            self.active_transfers[transfer_key]["chunks"][chunk_no] = payload
            self.stats["received"] += 1
            
            print(f"[{timestamp}] RX from {sender_id}@{addr[0]}: {filename} chunk {chunk_no+1}/{total_chunks}")
            
            # Check if transfer complete
            if len(self.active_transfers[transfer_key]["chunks"]) == total_chunks:
                self.reconstruct_file(transfer_key)
                
        except Exception as e:
            print(f"[{timestamp}] COLLISION/ERROR from {addr[0]}: {str(e)[:50]}")
            self.stats["collisions"] += 1
            
    def reconstruct_file(self, transfer_key):
        transfer = self.active_transfers[transfer_key]
        filename = transfer["filename"]
        chunks = transfer["chunks"]
        sender = transfer["sender"]
        
        output_path = f"received_{self.device_id}/from_{sender}_{filename}"
        
        with open(output_path, "wb") as f:
            for i in range(transfer["total"]):
                if i in chunks:
                    f.write(chunks[i])
                    
        elapsed = time.time() - transfer["start_time"]
        self.stats["completed"] += 1
        
        print(f"✓ COMPLETE: {filename} from {sender} ({elapsed:.2f}s)")
        print(f"  Saved to: {output_path}")
        print(f"  Stats: RX={self.stats['received']}, Collisions={self.stats['collisions']}, Complete={self.stats['completed']}")
        print("-" * 50)
        
        del self.active_transfers[transfer_key]

if __name__ == "__main__":
    import sys
    device_id = sys.argv[1] if len(sys.argv) > 1 else "RECV"
    receiver = ALOHAReceiver(device_id=device_id)
    receiver.start_listening()
