#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aliyun_face.py - 阿里云视觉智能开放平台人脸识别
"""

import sys
import hashlib
import hmac
import base64
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ============================================================
# 阿里云凭证
ACCESS_KEY_ID = "LTAI5tJwStftMmxKNNXC3bbi"
ACCESS_KEY_SECRET = "Bb6cOOmap0dNuPP849PXp62Iuyax7G"
REGION_ID = "cn-shanghai"

# 人脸库名称
DB_NAME = "home_family"

# 主人 EntityId
OWNER_ID = "zhangyanbo"

# ============================================================

def percent_encode(value):
    """阿里云 URL 编码规则"""
    if value is None:
        return ""
    return urllib.parse.quote(str(value), safe='')

def compute_signature(parameters, access_key_secret):
    """计算阿里云签名"""
    sorted_params = sorted(parameters.items())
    canonicalized = '&'.join(f'{percent_encode(k)}={percent_encode(v)}' for k, v in sorted_params)
    string_to_sign = f'POST&{percent_encode("/")}&{percent_encode(canonicalized)}'
    signature = base64.b64encode(
        hmac.new((access_key_secret + '&').encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()
    return signature

def call_api(action, params=None):
    """调用阿里云视觉智能 API"""
    nonce = str(hashlib.md5(datetime.now().isoformat().encode()).hexdigest())
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    base_params = {
        "AccessKeyId": ACCESS_KEY_ID,
        "Action": action,
        "Format": "JSON",
        "RegionId": REGION_ID,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": nonce,
        "SignatureVersion": "1.0",
        "Timestamp": timestamp,
        "Version": "2019-12-30"
    }
    
    if params:
        base_params.update(params)
    
    signature = compute_signature(base_params, ACCESS_KEY_SECRET)
    base_params["Signature"] = signature
    
    post_data = '&'.join(f'{percent_encode(k)}={percent_encode(v)}' for k, v in sorted(base_params.items()))
    url = 'https://facebody.cn-shanghai.aliyuncs.com/'
    
    req = urllib.request.Request(
        url,
        data=post_data.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def read_image_as_base64(image_path):
    """读取图片为 Base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def create_db():
    """创建人脸库"""
    result = call_api("CreateFaceDB", {"DBName": DB_NAME})
    print(json.dumps(result, ensure_ascii=False, indent=2))

def add_face(entity_id, image_path):
    """添加人脸到库"""
    image_base64 = read_image_as_base64(image_path)
    # 去掉 data:image/jpeg;base64,前缀，直接传 Base64
    result = call_api("AddFace", {
        "DbName": DB_NAME,
        "EntityId": entity_id,
        "ImageUrl": image_base64  # 直接传 Base64
    })
    print(json.dumps(result, ensure_ascii=False, indent=2))

def search_face(image_path):
    """搜索人脸 - 需要图片是 HTTP/HTTPS URL"""
    # 阿里云只接受 HTTP/HTTPS URL，不接受 Base64
    # 需要使用 OSS 或可公开访问的图片 URL
    print(json.dumps({
        "entity_id": None,
        "score": 0,
        "error": "需要图片 URL（HTTP/HTTPS），不支持 Base64"
    }))

def main():
    if len(sys.argv) < 2:
        print("用法：python3 aliyun_face.py <create_db|add_face|search> [args...]")
        print("  create_db                    - 创建人脸库")
        print("  add_face <entity_id> <image> - 添加人脸")
        print("  search <image>               - 搜索人脸")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "create_db":
        print("📌 创建人脸库...")
        create_db()
    elif action == "add_face":
        if len(sys.argv) < 4:
            print("用法：python3 aliyun_face.py add_face <entity_id> <image_path>")
            sys.exit(1)
        print(f"📌 添加人脸：{sys.argv[2]}")
        add_face(sys.argv[2], sys.argv[3])
    elif action == "search":
        if len(sys.argv) < 3:
            print("用法：python3 aliyun_face.py search <image_path>")
            sys.exit(1)
        print("🔍 识别人脸...")
        search_face(sys.argv[2])
    else:
        print(f"未知操作：{action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
