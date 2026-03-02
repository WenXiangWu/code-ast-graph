"""
测试 Claude SDK连接
"""
import requests
import time

def test_claude_connection():
    """测试 Claude SDK 是否能正常连接"""
    base_url = "http://localhost:18000"
    
    try:
        # 获取会话列表
        response = requests.get(f"{base_url}/api/sessions", timeout=10)
        if response.status_code == 200:
            sessions = response.json()
            print(f"✅ 成功获取会话列表，共 {len(sessions)} 个会话")
            
            if sessions:
                session = sessions[0]
                session_id = session['id']
                print(f"使用会话: {session_id}")
                
                # 发送测试消息
                test_data = {
                    "threadId": session_id,
                    "runId": f"test-run-{int(time.time())}",
                    "state": "running",
                    "messages": [
                        {
                            "id": "test-msg-1",
                            "role": "user",
                            "content": "Hello Claude SDK"
                        }
                    ],
                    "tools": [],
                    "context": [],
                    "forwardedProps": {}
                }
                
                print("发送测试消息...")
                response = requests.post(
                    f"{base_url}/api/chat/{session_id}",
                    json=test_data,
                    timeout=30
                )
                
                print(f"响应状态码: {response.status_code}")
                if response.status_code == 200:
                    print("✅测试请求发送成功")
                    print("请查看后端日志确认Claude SDK连接状态")
                else:
                    print(f"❌ 请求失败: {response.text}")
            else:
                print("❌没有可用会话")
        else:
            print(f"❌ 获取会话失败: {response.status_code}")
    except Exception as e:
        print(f"❌测试失败: {e}")

if __name__ == "__main__":
    test_claude_connection()