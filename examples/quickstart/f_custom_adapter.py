import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "third-party-adapter/acme_weather/adapter.py"
spec = importlib.util.spec_from_file_location("acme_weather", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)
adapter = module.AcmeWeatherAdapter({"air.temperature.celsius": 21.5})
adapter.start()
print(adapter.capabilities(), adapter.observe("air.temperature.celsius"))
adapter.stop()
