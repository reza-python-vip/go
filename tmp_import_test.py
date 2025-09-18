import sys
sys.path.insert(0, '/workspaces/go')
modules = ['src.config','src.utils','src.network_metrics','src.fetcher','src.tester_base','src.filter','src.main']
for m in modules:
    try:
        __import__(m)
        print('OK', m)
    except Exception as e:
        print('ERR', m, e)
        raise
print('ALL_IMPORTS_DONE')
