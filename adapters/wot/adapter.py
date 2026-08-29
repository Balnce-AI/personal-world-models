def thing_description_capabilities(td:dict)->list[dict]:
    title=td.get("title","unknown")
    caps=[]
    for name in td.get("properties",{}): caps.append({"kind":"PROPERTY","name":name,"sourceThing":title})
    for name in td.get("actions",{}): caps.append({"kind":"ACTION","name":name,"sourceThing":title})
    for name in td.get("events",{}): caps.append({"kind":"EVENT","name":name,"sourceThing":title})
    return caps
