DEFAULT_MAP={
  "Vehicle.Cabin.HVAC.Station.Row1.Left.Temperature": "vehicle.cabin.temperature.driver",
  "Vehicle.Speed": "vehicle.motion.speed",
  "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current": "vehicle.energy.soc",
}

def map_signal(vss_path:str, value, mapping=None):
    mapping=mapping or DEFAULT_MAP
    if vss_path not in mapping:
        return {"status":"UNKNOWN_EXTERNAL_SEMANTIC","externalPath":vss_path,"value":value}
    return {"status":"MAPPED","externalPath":vss_path,"internalSemantic":mapping[vss_path],"value":value}
