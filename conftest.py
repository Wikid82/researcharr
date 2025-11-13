import os

ORDER_F='ordering_nodeids_window.txt'
if os.path.exists(ORDER_F):
    ordering=[l.strip() for l in open(ORDER_F).read().splitlines() if l.strip()]
else:
    ordering=[]
order_index={node:i for i,node in enumerate(ordering)}

def pytest_collection_modifyitems(session, config, items):
    if not ordering:
        return
    def idx(item):
        n=item.nodeid
        if n in order_index:
            return order_index[n]
        for node,i in order_index.items():
            if node==n:
                return i
            if '::' in node and node.split('::')[0]==item.fspath.strpath:
                return i
        return len(order_index)+1000
    items.sort(key=idx)
