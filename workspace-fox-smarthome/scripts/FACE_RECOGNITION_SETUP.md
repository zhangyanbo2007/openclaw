# 人脸识别配置指南

## 问题诊断

当前 AccessKey (`LTAI5tDvdyose9UQdkojDxXZ`) 返回 `InvalidAccessKeyId.AccessPolicyDenied` 错误。

## 解决步骤

### 步骤 1: 确认 RAM 用户权限

1. 登录阿里云 RAM 控制台：https://ram.console.aliyun.com/
2. 进入 **用户** 页面
3. 找到 AccessKey ID `LTAI5tDvdyose9UQdkojDxXZ` 对应的用户
4. 点击 **添加权限**
5. 添加以下权限：
   - `AliyunVisionFullAccess` (视觉智能开放平台完全访问权限)
   - 或自定义权限，包含：
     ```json
     {
       "Version": "1",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": ["facebody:*"],
           "Resource": "*"
         }
       ]
     }
     ```

### 步骤 2: 确认视觉智能服务开通

1. 访问：https://vision.console.aliyun.com/cn-shanghai/detail/facebody
2. 确认 **人脸搜索** 服务已开通
3. 确认账户余额充足（每月 2000 次免费额度）

### 步骤 3: 在 OpenAPI Explorer 测试

1. 访问：https://next.api.alibabacloud.com/api/facebody/2019-12-30/SearchFace
2. 使用你的 AccessKey 登录
3. 填写参数：
   - DbName: `home_family_db`
   - ImageUrl: 上传测试图片
   - Num: `1`
   - Threshold: `80`
4. 点击 **运行** 测试

### 步骤 4: 录入人脸

测试成功后，先录入你的人脸：

```bash
cd /home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts

# 准备你的人脸照片（正面、清晰）
# 然后运行：
python3 aliyun_face.py add_face zhangyanbo /path/to/your_photo.jpg
```

### 步骤 5: 测试识别

```bash
python3 aliyun_face.py search /tmp/openclaw/face_test.jpg
```

预期输出：
```json
{"entity_id": "zhangyanbo", "score": 95.5}
```

## 脚本说明

| 文件 | 作用 |
|------|------|
| `aliyun_face.py` | 人脸识别脚本 |
| `door_handler.sh` | 进出门处理主脚本 |
| `ezviz_doorbell.sh` | 猫眼抓图脚本 |

## 常见问题

### Q: InvalidAccessKeyId.AccessPolicyDenied
A: AccessKey 没有访问视觉智能平台的权限，需要在 RAM 控制台添加权限。

### Q: InvalidParameter.ImageEmpty
A: 图片为空或格式不正确，确保图片是有效的 JPEG/PNG 格式。

### Q: InvalidParameter.DbName
A: 人脸库不存在，先运行 `python3 aliyun_face.py create_db` 创建人脸库。

### Q: FaceNotDetected
A: 图片中没有检测到人脸，确保照片中有人脸且清晰。

## 联系支持

如果问题持续，访问：
- 阿里云工单：https://workorder.console.aliyun.com/
- 视觉智能文档：https://help.aliyun.com/product/44288.html
