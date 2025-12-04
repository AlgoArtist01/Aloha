# Minimal Slotted ALOHA (simplified)
import random, time

# config
NODES = 10
SLOTS = 2000
ARRIVAL = 0.02
MAX_EXP = 6

def run_sim():
    created = [None]*NODES     # slot when packet arrived (None => no packet)
    attempts = [0]*NODES       # retry count
    backoff = [0]*NODES        # slots to wait before next try

    succ = col = empty = 0
    delays = []

    for slot in range(1, SLOTS+1):
        # new arrivals
        for i in range(NODES):
            if created[i] is None and random.random() < ARRIVAL:
                created[i] = slot
                attempts[i] = 0
                backoff[i] = 0

        # who transmits now?
        tx = [i for i in range(NODES) if created[i] is not None and backoff[i] == 0]

        if not tx:
            empty += 1
        elif len(tx) == 1:
            i = tx[0]
            succ += 1
            delays.append(slot - created[i] + 1)
            created[i] = None
            attempts[i] = backoff[i] = 0
        else:
            col += 1
            for i in tx:
                attempts[i] += 1
                exp = min(attempts[i], MAX_EXP)
                w = 2 ** exp
                backoff[i] = random.randint(1, w-1) if w > 1 else 0

        # tick down backoffs
        for i in range(NODES):
            if backoff[i] > 0:
                backoff[i] -= 1

    throughput = succ / SLOTS
    active_slots = SLOTS - empty
    coll_rate = (col / active_slots) if active_slots else 0
    avg_delay = (sum(delays) / len(delays)) if delays else float('nan')

    print(f"Slots={SLOTS}, Nodes={NODES}")
    print(f"Successes={succ}, Collisions={col}, Empty={empty}")
    print(f"Throughput={throughput:.4f}, Collision rate={coll_rate:.4f}, Avg delay={avg_delay:.2f}")

if __name__ == "__main__":
    t0 = time.time()
    run_sim()
    print("Time:", round(time.time()-t0, 3), "s")
