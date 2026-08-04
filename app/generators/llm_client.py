#把你传进来的 messages 发送给大模型接口，然后把模型回复的文本提取出来返回。
import json
from urllib import request, error

from app.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_TIMEOUT


def chat_completion(messages: list[dict]) -> str:
    url = f"{LLM_BASE_URL}/chat/completions"

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.2
    }

    data = json.dumps(payload).encode("utf-8")

    req = request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",#我这次发送的数据是 JSON 格式
            "Authorization": f"Bearer {LLM_API_KEY}"#用 Bearer Token 方式把 API key 发给模型服务
        },
        method="POST"
    )

    try:
        #with as resp:请求成功后，把响应对象记作 resp
        with request.urlopen(req, timeout=LLM_TIMEOUT) as resp:#把刚才构造好的请求发出去，并且最多等 LLM_TIMEOUT 秒
            result = json.loads(resp.read().decode("utf-8"))#拿到大模型返回的 JSON，并转成 Python 可以操作的字典
    except error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"大模型请求失败，HTTP {e.code}: {detail}")
    except error.URLError as e:
        raise RuntimeError(f"无法连接到大模型服务: {e.reason}")

    return result["choices"][0]["message"]["content"].strip()
# result["choices"]：AI 可能给了好几个答案，这里是个列表。
# [0]：我们要列表里的第一个（最棒的）答案。
# ["message"]：在这个答案里找“消息内容”这个字典键。
# ["content"]：终于拿到 AI 写的那段文字了！
# .strip()：顺手把前后的空格、换行符删掉，干干净净。