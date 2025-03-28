from pydantic import BaseModel
from typing import List, Optional


class EmailAddress(BaseModel):
    address: str

class EmailRecipients(BaseModel):
    to: List[EmailAddress]
    
    def getFirst(self):
        if self.to is not None:
            return self.to[0].address
        else:
            return None

class EmailContent(BaseModel):
    subject: str
    plainText: str
    html: Optional[str] = None


class EmailMessage(BaseModel):
    senderAddress: str
    recipients: EmailRecipients
    content: EmailContent
    senderName: Optional[str]
    
    def create_auto_reply(self) -> 'EmailMessage':
        """
        問い合わせ元に送信する自動返信メールを作成するメソッド
        
        Returns:
            EmailMessage: 自動返信用のEmailMessageインスタンス
        """
        # 送信元アドレスと送信先を入れ替え
        recipient_address = self.recipients.getFirst()
        
        # 自動返信用のインスタンスを作成
        auto_reply = EmailMessage(
            senderAddress=self.senderAddress,
            recipients=EmailRecipients(
                to=[EmailAddress(address=recipient_address)]
            ),
            content=EmailContent(
                subject=f"【ryu-nakamura.com】お問い合わせありがとうございます",
                plainText=self._create_auto_reply_text(),
                html=self._create_auto_reply_html()
            ),
            senderName="自動返信システム"  # 送信者名を設定
        )
        
        return auto_reply
    
    def _create_auto_reply_text(self) -> str:
        """自動返信メールのプレーンテキスト本文を作成する"""
        return f"""
{self.senderName} 様

この度はお問い合わせいただき、誠にありがとうございます。
下記の内容でお問い合わせを受け付けました。

[お問い合わせ内容]
件名: {self.content.subject}
メッセージ:
{self.content.plainText}

内容を確認の上、担当者より折り返しご連絡させていただきます。
通常2営業日以内にご返信いたしますので、今しばらくお待ちくださいませ。

なお、このメールは自動送信されております。
このメールに返信されても対応できかねますのでご了承ください。

------------------------------
中村システムエンジニアリング事業所
〒101-0024 東京都千代田区神田和泉町1番地6-16ヤマトビル405
Email: dahlia1209@gmail.com
URL: https://www.ryu-nakamura.com
------------------------------
        """
    
    def _create_auto_reply_html(self) -> str:
        """自動返信メールのHTML本文を作成する"""
        return f"""
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; line-height: 1.6; }}
    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
    .header {{ margin-bottom: 20px; }}
    .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 5px; }}
    .inquiry-details {{ background-color: #fff; padding: 15px; border-left: 4px solid #0078d4; margin: 15px 0; }}
    .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2>{self.senderName} 様</h2>
    </div>
    
    <div class="content">
      <p>この度はお問い合わせいただき、誠にありがとうございます。</p>
      <p>下記の内容でお問い合わせを受け付けました。</p>
      
      <div class="inquiry-details">
        <p><strong>件名:</strong> {self.content.subject}</p>
        <p><strong>メッセージ:</strong></p>
        <p>{self.content.plainText.replace(chr(10), "<br>")}</p>
      </div>
      
      <p>内容を確認の上、担当者より折り返しご連絡させていただきます。</p>
      <p>通常2営業日以内にご返信いたしますので、今しばらくお待ちくださいませ。</p>
      
      <p><em>なお、このメールは自動送信されております。<br>
      このメールに返信されても対応できかねますのでご了承ください。</em></p>
    </div>
    
    <div class="footer">
      <p>------------------------------</p>
      <p><strong>中村システムエンジニアリング事業所</strong></p>
      <p>〒101-0024 東京都千代田区神田和泉町1番地6-16ヤマトビル405</p>
      <p>Email: dahlia1209@gmail.com</p>
      <p>URL: <a href="https://www.ryu-nakamura.com">https://www.ryu-nakamura.com</a></p>
      <p>------------------------------</p>
    </div>
  </div>
</body>
</html>
        """
        
    def create_admin_notification(self, admin_email: str) -> 'EmailMessage':
        """
        管理者に送信する問い合わせ通知メールを作成するメソッド
        
        Args:
            admin_email: 管理者のメールアドレス
            
        Returns:
            EmailMessage: 管理者通知用のEmailMessageインスタンス
        """
        # 管理者向けの通知メッセージを作成
        admin_message = EmailMessage(
            senderAddress=self.senderAddress,
            recipients=EmailRecipients(
                to=[EmailAddress(address=admin_email)]
            ),
            content=EmailContent(
                subject=f"【ryu-nakamura.com】問い合わせ通知",
                plainText=self._create_admin_notification_text(),
                html=self._create_admin_notification_html()
            ),
            senderName="問い合わせ通知システム"
        )
        
        return admin_message
    
    def _create_admin_notification_text(self) -> str:
        """管理者向け通知メールのプレーンテキスト本文を作成する"""
        timestamp = __import__('datetime').datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        
        return f"""
【新規お問い合わせ】

ウェブサイトから新しいお問い合わせが届きました。

■ お名前: {self.senderName or "未入力"}
■ メールアドレス: {self.recipients.getFirst() or "未入力"}
■ 件名: {self.content.subject}
■ 受付日時: {timestamp}

■ メッセージ内容:
{self.content.plainText}

---
※このメールはシステムからの自動送信です。
※お問い合わせへの対応をお願いいたします。
        """
    
    def _create_admin_notification_html(self) -> str:
        """管理者向け通知メールのHTML本文を作成する"""
        timestamp = __import__('datetime').datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        
        return f"""
<html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; line-height: 1.6; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #0078d4; color: white; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
            .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 5px; }}
            .info-item {{ margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
            .message-box {{ background-color: #fff; padding: 15px; border-left: 4px solid #0078d4; margin: 15px 0; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
            .timestamp {{ color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin: 0;">新規お問い合わせ</h2>
            </div>
            
            <div class="content">
                <p>ウェブサイトから新しいお問い合わせが届きました。</p>
                
                <div class="info-item">
                    <strong>お名前:</strong> {self.senderName or "未入力"}
                </div>
                
                <div class="info-item">
                    <strong>メールアドレス:</strong> {self.recipients.getFirst() or "未入力"}
                </div>
                
                <div class="info-item">
                    <strong>件名:</strong> {self.content.subject}
                </div>
                
                <div class="info-item">
                    <strong>受付日時:</strong> <span class="timestamp">{timestamp}</span>
                </div>
                
                <div>
                    <strong>メッセージ内容:</strong>
                    <div class="message-box">
                        {self.content.plainText.replace(chr(10), '<br>')}
                    </div>
                </div>
                
                <p>このメールは問い合わせフォームからの送信内容を通知するものです。</p>
            </div>
            
            <div class="footer">
                <p>※このメールはシステムからの自動送信です。</p>
                <p>※お問い合わせへの対応をお願いいたします。</p>
            </div>
        </div>
    </body>
</html>
        """
    
    


class EmailResponse(BaseModel):
    id: str
    status: str
    error: Optional[None] = None
    