import numpy as np

def entropy(values):
    probs = np.array(values) / sum(values)
    return -np.sum(probs * np.log(probs + 1e-9))

def flow_energy(inflow, outflow):
    return abs(inflow - outflow)

if __name__ == "__main__":
    print("Flow engine ready")
