import sys
sys.path.insert(0, 'D:/00_source/30_Python312/13_AGENT_CC/backend')

from app.api.v1 import knowledge

print("knowledge模块导入成功")
print(f"router对象: {knowledge.router}")
print(f"路由数量: {len(knowledge.router.routes)}")
for route in knowledge.router.routes:
    print(f"  - {route.path} [{','.join(route.methods)}]")
