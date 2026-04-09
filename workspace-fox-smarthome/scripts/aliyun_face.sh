#!/bin/bash
# 阿里云人脸识别 - 人脸库管理脚本
# 用法：
#   ./aliyun_face.sh add <image_path> <person_id>  # 添加人脸
#   ./aliyun_face.sh search <image_path>           # 搜索人脸
#   ./aliyun_face.sh delete <person_id>            # 删除人员

AK_ID="LTAI5tDvdyose9UQdkojDxXZ"
AK_SECRET="y9HZr4tbFgZzexKHYJWDFnAxkEfB62"
REGION="cn-shanghai"
FACE_DB="home_family"

# 获取 API Token
get_token() {
  local ts=$(date +%s000)
  local sign_str="GET&%2F&AccessKeyId%3D$AK_ID%26Action%3DGetToken%26Format%3DJSON%26Region%3D$REGION%26SignatureMethod%3DHMAC-SHA1%26SignatureNonce%3D$ts%26SignatureVersion%3D1.0%26Timestamp%3D$(date -u -d "+8 hours" +%Y-%m-%dT%H%%3A%M%%3ASZ)&Secret=$AK_SECRET"
  local signature=$(echo -n "$sign_str" | openssl dgst -sha1 -hmac "$AK_SECRET&" -binary | base64 | tr '+' '%2B' | tr '/' '%2F' | tr '=' '%3D')
  
  # 简化：直接用 AppCode 方式
  echo ""
}

# 人脸搜索 API（使用 AppCode 认证）
face_search() {
  local image_file="$1"
  local appcode="APPCODE af2b85c6d69f4b7e9c7d9f5e3b4a8c1d"
  
  # 将图片转为 Base64
  local image_base64=$(base64 -w 0 "$image_file")
  
  local response=$(curl -s -X POST "https://facebody.cn-shanghai.aliyuncs.com/face/aliyun/face_search" \
    -H "Authorization: APPCODE af2b85c6d69f4b7e9c7d9f5e3b4a8c1d" \
    -H "Content-Type: application/json" \
    -d "{
      \"ImageUrl\": \"\",
      \"ImageBase64\": \"$image_base64\",
      \"FaceDatabaseName\": \"$FACE_DB\",
      \"ReturnFaceData\": true,
      \"TopN\": 1
    }")
  
  echo "$response"
}

# 添加人脸到人脸库
face_add() {
  local image_file="$1"
  local person_id="$2"
  local image_base64=$(base64 -w 0 "$image_file")
  
  local response=$(curl -s -X POST "https://facebody.cn-shanghai.aliyuncs.com/face/aliyun/face_add" \
    -H "Authorization: APPCODE af2b85c6d69f4b7e9c7d9f5e3b4a8c1d" \
    -H "Content-Type: application/json" \
    -d "{
      \"ImageUrl\": \"\",
      \"ImageBase64\": \"$image_base64\",
      \"FaceDatabaseName\": \"$FACE_DB\",
      \"PersonId\": \"$person_id\"
    }")
  
  echo "$response"
}

# 从人脸库删除人员
face_delete() {
  local person_id="$1"
  
  local response=$(curl -s -X POST "https://facebody.cn-shanghai.aliyuncs.com/face/aliyun/face_delete" \
    -H "Authorization: APPCODE af2b85c6d69f4b7e9c7d9f5e3b4a8c1d" \
    -H "Content-Type: application/json" \
    -d "{
      \"FaceDatabaseName\": \"$FACE_DB\",
      \"PersonId\": \"$person_id\"
    }")
  
  echo "$response"
}

# 主命令处理
case "$1" in
  add)
    if [ -z "$2" ] || [ -z "$3" ]; then
      echo "用法: $0 add <image_path> <person_id>"
      exit 1
    fi
    face_add "$2" "$3"
    ;;
  search)
    if [ -z "$2" ]; then
      echo "用法: $0 search <image_path>"
      exit 1
    fi
    face_search "$2"
    ;;
  delete)
    if [ -z "$2" ]; then
      echo "用法: $0 delete <person_id>"
      exit 1
    fi
    face_delete "$2"
    ;;
  *)
    echo "阿里云人脸识别工具"
    echo "用法:"
    echo "  $0 add <image_path> <person_id>   # 添加人脸到人脸库"
    echo "  $0 search <image_path>            # 搜索人脸"
    echo "  $0 delete <person_id>             # 从人脸库删除人员"
    ;;
esac