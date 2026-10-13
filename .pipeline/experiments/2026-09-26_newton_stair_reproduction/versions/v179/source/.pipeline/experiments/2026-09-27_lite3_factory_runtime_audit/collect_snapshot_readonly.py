import pathlib,json,base64,hashlib,datetime,subprocess,os
root=pathlib.Path('/home/ysc/jy_exe')
paths=['bin/jy_exe', 'lib/ras_lib/libdeepras.so', 'jy_exe', 'libdeepras.so', 'scripts/run.sh', 'jy_exe.service', 'conf/name.toml', 'conf/motor.toml', 'conf/Algorithm.toml', 'conf/model_config.yaml']
for rel in paths:
 p=root/rel;data=p.read_bytes()
 print(json.dumps({'relative_path':rel,'remote_path':str(p),'resolved_remote_path':str(p.resolve()),'is_symlink':p.is_symlink(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'acquired_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_base64':base64.b64encode(data).decode()}),flush=True)
