set pagination off
set confirm off
set print thread-events off
set print elements 32
set disable-randomization off
handle SIGPIPE nostop noprint pass
handle SIGINT nostop noprint pass
handle SIGTERM nostop noprint pass
python
import gdb, os, json, signal
status_path=os.environ['V287_DEBUG_STATUS']
log_path=os.environ['V287_DEBUG_LOG']
gdb.execute('set logging file '+log_path)
gdb.execute('set logging overwrite on')
gdb.execute('set logging on')
state={'signal':None,'exit_code':None}
def stopped(event):
    if isinstance(event,gdb.SignalEvent):
        state['signal']=event.stop_signal
        gdb.write('\nV287_NATIVE_SIGNAL '+event.stop_signal+'\n')
        for command in ('thread apply all bt full','info registers','info sharedlibrary'):
            try:gdb.execute(command)
            except gdb.error as error:gdb.write(str(error)+'\n')
def exited(event):
    state['exit_code']=getattr(event,'exit_code',None)
gdb.events.stop.connect(stopped)
gdb.events.exited.connect(exited)
end
run
python
with open(status_path,'w') as output:json.dump(state,output,indent=2)
if state['signal']:
    gdb.execute('kill')
    gdb.execute('quit '+str(128+getattr(signal,state['signal'])))
else:
    gdb.execute('quit '+str(state['exit_code'] if state['exit_code'] is not None else 1))
end
