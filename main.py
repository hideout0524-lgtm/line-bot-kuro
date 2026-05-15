from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent
)
import anthropic
import os
import base64

app = Flask(__name__)

configuration = Configuration(access_token=os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))
anthropic_client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        user_message = event.message.text

        response = anthropic_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system="あなたはボスの個人秘書「クロ」です。日本語で簡潔に回答してください。塾経営・AI副業・YouTube運営のサポートが得意です。",
            messages=[{"role": "user", "content": user_message}]
        )

        reply_text = response.content[0].text

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_blob_api = MessagingApiBlob(api_client)

        image_content = line_bot_blob_api.get_message_content(event.message.id)
        image_data = base64.standard_b64encode(image_content).decode('utf-8')

        response = anthropic_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system="あなたはボスの個人秘書「クロ」です。レシートや領収書の画像が送られてきた場合は、日付・店名・金額・品目を抽出して経費として整理してください。日本語で回答してください。",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": "このレシートの情報を整理してください。"
                    }
                ]
            }]
        )

        reply_text = response.content[0].text

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
