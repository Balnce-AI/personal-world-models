from common import model
from pwm_hpl_ref.simulation import SimulationSource, SimulationStep

source = SimulationSource((SimulationStep(0, "entity.put", {"id": "simulated", "type": "Device"}),))
with model() as pwm:
    source.emit(pwm)
    print(pwm.materialize().entities)
