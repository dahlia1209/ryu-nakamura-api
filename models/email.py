from pydantic import BaseModel
from typing import List, Optional
from bs4 import BeautifulSoup
import os

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
    
    @classmethod
    def create_purchased_order_reply(
        self,to_address:str,
        name:str,order_id:str,order_date:str,content_title:str,price:str,payment_method:str,content_html:str
    ):
        def _create_html() -> str:
            def body(header:str="",main:str="",footer:str=""):
                return f"""
                <body style="margin:0;padding:0;font-size:14px;font-family:sans-serif;background-color:#fff;">
                    <div class="wrapper" style="margin:0;padding:0;word-break:break-all;background-color:#fff">
                    {header}
                    {main}
                    {footer}
                    </div>
                </body>
                """
            
            def header():
                return f"""
                <div class="mailer-header" style="padding-top:24px;padding-right:16px;padding-left:16px;margin-bottom:24px;text-align:center;background-color:#fff;">
                    <table style="width:100%;max-width:600px;margin-right:auto;margin-left:auto">
                        <tr>
                            <td style="text-align:center;vertical-align:middle">
                                <a href="https://www.ryu-nakamura.com" style="color:#787c7b;text-decoration:none;">
                                <!-- <img height="20" alt="note" src="https://assets.st-note.com/poc-image/manual/production/logo_202212.png"> -->
                                Ryu Nakamura
                                </a>
                            </td>
                        </tr>
                    </table>
                </div>

                """
            
            def main(title:str,order:str,content:str,author:str,recomend:str):
                return f"""
                <div class="main" style="padding-left:16px;padding-right:16px">
                    <table style="width:100%;max-width:600px;margin-left:auto;margin-right:auto">
                        <tr>
                            <td>
                            {title}
                            {order}
                            {content}
                            {author}
                            {recomend}
                            </td>
                        </tr>
                    </table>
                </div>
                
                """
            
            def main_title(name:str=name):
                return f"""
                <div class="title" style="margin-bottom:16px">
                <table style="width:100%">
                    <tr>
                    <td>
                        <div class="title__text" style="font-size:16px">
                        <strong>{name}</strong> さん<br>
                        サイトをご利用いただき、ありがとうございます。<br>
                        ご購入の詳細は以下のとおりです。
                        </div>
                    </td>
                    </tr>
                </table>
                </div>
                """
            
            def main_order(order_id:str=order_id,order_date:str=order_date,content_title:str=content_title,price:str=price,payment_method:str=payment_method):
                return f"""
                <div class="card" style="border:1px solid #e6e6e6;background-color:#fff;border-radius:4px">
                <table style="width:100%;margin-left:auto;margin-right:auto">
                    <tr>
                    <td class="card__body" style="padding:24px">
                        <div class="informationList" style="margin-bottom:0">
                        <div class="informationList__item" style="margin-bottom:16px">
                            <b class="informationList__caption" style="display:block">注文ID</b>
                            {order_id}
                        </div>
                        <div class="informationList__item" style="margin-bottom:16px">
                            <b class="informationList__caption" style="display:block">注文日時</b>
                            {order_date}
                        </div>
                        <div class="informationList__item" style="margin-bottom:16px">
                            <b class="informationList__caption" style="display:block">商品</b>
                            {content_title}
                        </div>
                        <div class="informationList__item" style="margin-bottom:16px">
                            <b class="informationList__caption" style="display:block">支払額</b>
                            {price}円
                        </div>
                        <div class="informationList__item" style="margin-bottom:0">
                            <b class="informationList__caption" style="display:block">決済方法</b>
                            {payment_method}
                        </div>
                        </div>
                    </td>
                    </tr>
                </table>
                </div>
                """
            
            def main_content(content_html:str=content_html):
                return f"""
                <div class="card" style="border:1px solid #e6e6e6;background-color:#fff;border-radius:4px;margin-top:16px">
                <table style="width:100%;margin-left:auto;margin-right:auto">
                    <tr>
                    <td class="card__body card__body--article" style="padding:16px;width:100%;max-width:568px;word-break:break-word">
                        {content_html}
                    </td>
                    </tr>
                </table>
                </div>
                """
            
            def main_author():
                return f""" 
                
                """
            
            def main_recomend():
                return f"""
                
                """
            
            def footer():
                return f"""
                <div class="mailer-footer" style="padding-right:16px;padding-left:16px">
                    <table style="width:100%;max-width:600px;margin-right:auto;margin-left:auto">
                        <tr>
                            <td>
                                <p class="mailer-footer__menu" style="padding-top:32px;padding-bottom:16px;font-size:14px;line-height:2">
                                
                                </p>
                                <p class="mailer-footer__copyright" style="padding-top:16px;padding-bottom:40px;font-size:12px;color:#787c7b;border-top:1px solid #e6e6e6">
                                <a href="https://www.ryu-nakamura.com/" style="color:#787c7b;text-decoration:none;">© 2025 中村システムエンジニアリング事業所.</a>
                                </p>
                            </td>
                        </tr>
                    </table>
                </div>
                """
                
            main_element=main(main_title(),main_order(),main_content(),main_author(),main_recomend())
            return body(header(),main_element,footer())
                
        
        # 自動返信用のインスタンスを作成
        soup = BeautifulSoup(_create_html(), 'html.parser')
        reply = EmailMessage(
            senderAddress=os.getenv('SENDER_ADDRESS'),
            recipients=EmailRecipients(
                to=[EmailAddress(address=to_address)]
            ),
            content=EmailContent(
                subject=f"【ryu-nakamura.com】ご購入が完了いたしました ",
                plainText=soup.get_text(),
                html=str(soup)
            ),
            senderName="自動返信システム"  
        )
        
        return reply
        

class EmailResponse(BaseModel):
    id: str
    status: str
    error: Optional[None] = None
    