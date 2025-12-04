
"""
ALOHA combined sender/receiver

Usage examples:
  # Run receiver (listens on UDP port 5005):
  python aloha.py recv --device RECV --port 5005

  # Send a file to a receiver at 192.168.0.10 port 5005
  python aloha.py send 192.168.0.10 file.bin --port 5005 --sender-id SNDR --delay 0.05

This single-file tool uses the same wire format as the earlier receiver:
  sender_id (4 bytes ASCII) + chunk_no (4 bytes big) + total_chunks (4 bytes big)
  + filename_len (2 bytes big) + filename (bytes) + payload

Ctrl+C is handled gracefully for both sender and receiver.
"""
import os
import socket
import sys
import time
import threading
from datetime import datetime

# List of known device IPs on your local network. Update this list to match
# the IP addresses of other devices running `aloha.py`.
# Example: DEFAULT_TARGETS = ["192.168.1.10", "192.168.1.11"]
DEFAULT_TARGETS = []

# --- Configuration (no CLI) ---
# Set MODE to 'recv' to run receiver, or 'send' to send a file.
# If MODE == 'send', configure SEND_TARGETS (list) or leave empty to use DEFAULT_TARGETS.
MODE = 'recv'            # 'recv' or 'send'
PORT = 5005
DEVICE_ID = 'RECV'

# Send mode configuration
SEND_TARGETS = []        # e.g. ['192.168.1.10','192.168.1.11']
SEND_FILE = 'testfile.bin'
SENDER_ID = 'SNDR'
DELAY = 0.05
CHUNK_SIZE = 7000

# If SEND_TARGETS is empty, fall back to DEFAULT_TARGETS
if MODE == 'send' and not SEND_TARGETS:
    SEND_TARGETS = list(DEFAULT_TARGETS)
# ------------------------------


class ALOHAReceiver:
    def __init__(self, port=5005, device_id="RECV", buffer_size=8192):
        self.port = port
        self.device_id = device_id
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # bind and use a short timeout so the loop can respond to Ctrl+C
        self.sock.bind(("", port))
        self.sock.settimeout(1.0)
        self.active_transfers = {}
        self.stats = {"received": 0, "collisions": 0, "completed": 0}
        self.running = False

    def start_listening(self):
        print(f"[{self.device_id}] ALOHA Receiver listening on UDP port {self.port}")
        print(f"[{self.device_id}] Started at: {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 50)

        self.running = True
        try:
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(8192)
                except socket.timeout:
                    # timeout to allow checking for signals/flags
                    continue
                except OSError:
                    # socket closed or other OS error
                    break

                try:
                    self.process_packet(data, addr)
                except Exception as e:
                    # protect listener loop from packet processing errors
                    print(f"Error processing packet: {e}")
        except KeyboardInterrupt:
            print(f"\n[{self.device_id}] KeyboardInterrupt received, shutting down...")
        finally:
            self.running = False
            try:
                self.sock.close()
            except Exception:
                pass
            print(f"[{self.device_id}] Socket closed. Exiting.")

    def process_packet(self, data, addr):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]

        try:
            # Parse header: sender_id(4) + chunk_no(4) + total_chunks(4) + filename_len(2)
            sender_id = data[:4].decode(errors='ignore')
            chunk_no = int.from_bytes(data[4:8], "big")
            total_chunks = int.from_bytes(data[8:12], "big")
            filename_len = int.from_bytes(data[12:14], "big")
            filename = data[14:14+filename_len].decode(errors='ignore')
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


class ALOHASender:
    def __init__(self, target_host, port=5005, sender_id='SNDR'):
        self.target = (target_host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Ensure sender_id is exactly 4 bytes (pad or truncate)
        sid = sender_id.encode(errors='ignore')
        if len(sid) < 4:
            sid = sid.ljust(4, b'_')
        elif len(sid) > 4:
            sid = sid[:4]
        self.sender_id = sid

    def send_file(self, filepath, chunk_size=7000, delay=0.05):
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return

        fname = os.path.basename(filepath)
        fname_b = fname.encode()
        fname_len = len(fname_b)

        with open(filepath, 'rb') as f:
            data = f.read()

        # split into chunks
        chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
        total = len(chunks)

        print(f"Sending {fname} -> {self.target[0]}:{self.target[1]} ({len(data)} bytes in {total} chunks)")

        try:
            for i,chunk in enumerate(chunks):
                # header: sender_id(4) + chunk_no(4) + total_chunks(4) + filename_len(2) + filename + payload
                pkt = b''.join([
                    self.sender_id,
                    i.to_bytes(4, 'big'),
                    total.to_bytes(4, 'big'),
                    fname_len.to_bytes(2, 'big'),
                    fname_b,
                    chunk
                ])
                self.sock.sendto(pkt, self.target)
                print(f"Sent chunk {i+1}/{total}", end='\r')
                time.sleep(delay)
            print('\nSend complete.')
        except KeyboardInterrupt:
            print('\nSend interrupted by user (KeyboardInterrupt).')
        finally:
            try:
                self.sock.close()
            except Exception:
                pass


def run_from_config():
    """Run sender or receiver using the static configuration at the top of this file.

    This removes the CLI and relies on the constants defined in the configuration
    section. It is intended for simple deployments where other devices run the
    same script with matching `SEND_TARGETS`/`DEFAULT_TARGETS` values.
    """
    if MODE == 'recv':
        r = ALOHAReceiver(port=PORT, device_id=DEVICE_ID)
        r.start_listening()
    elif MODE == 'send':
        targets = list(SEND_TARGETS)
        if not targets:
            raise SystemExit('No targets configured for send mode (SEND_TARGETS or DEFAULT_TARGETS).')

        threads = []
        for tgt in targets:
            def _send_to(tgt_addr):
                sender = ALOHASender(tgt_addr, port=PORT, sender_id=SENDER_ID)
                sender.send_file(SEND_FILE, chunk_size=CHUNK_SIZE, delay=DELAY)

            th = threading.Thread(target=_send_to, args=(tgt,))
            th.start()
            threads.append(th)

        for th in threads:
            th.join()


if __name__ == '__main__':
    run_from_config()
