#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/11 16:11
# @Author  : zhoushuke
# @mail    : zhoushuke@sensetime.com
# @Site    :
# @File    : sendxmail.py
# @Software: PyCharm
# @Midofy  : 2020/04/20 20:00
# @Version : v1.1.2

import os
import logging
import urllib

logging.basicConfig(level=logging.DEBUG,
                    filename="/var/log/sendxmail.log",
                    filemode="a",
                    format="%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s"
                    )


class MailService(object):
    def __init__(self, base_url):
        self.base_url = base_url

    def send(self, dst, subject, fmt, content):
        url = self.base_url
        data = {
            "tos": dst,
            "subject": subject,
            "format": fmt,
            "content": content
        }
        try:
            data = urllib.urlencode(data).encode("utf-8")
            res = urllib.urlopen(url, data)
        except Exception as e:
            logging.error("Send mail failed, exception: {}, mail content: {}".format(e, content))
            os._exit(1)
        else:
            res_content = res.read()
            if res_content and "ok" in res_content:
                logging.info("Send mail successfully")
            else:
                logging.error("Mail response not OK, content: {}".format(str(res_content)))

    @staticmethod
    def _gen_html_head():
        htmlhead = """
        <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        </head>
        <style>
        table#t01 tr:nth-child(even) {
            background-color: #eee;
        }
        table#t01 tr:nth-child(odd) {
            background-color: #eee;
        }
        table#t02 tr:nth-child(odd) {
            background-color: #eee;
        }
        table#t02 tr:nth-child(even) {
            background-color: #eee;
        }
        """
        return htmlhead

    @staticmethod
    def _gen_html_table_head(title):
        tth = """
        table#t01 th {
            background-color: #00b5c8;
            color: white;
        }
        table#t02 th {
            background-color: #f58500;
            color: white;
        }"""
        th = """
        </style>
        <body style="background-color:#f2f3f2;">
            <table cellpadding="0" cellspacing="0" border="0" id="backgroundTable" width="100%" style="background-color:#f2f3f2;">
                <tr>
                    <td>
                        <table cellpadding="0" cellspacing="0" border="0" align="center" width="1000" style="background-color:#ffffff;">
                            <tr>
                                <td width="1000" valign="top" style="background-color:#00b5c8">
                                    <table cellpadding="0" cellspacing="0" border="0" align="center" width="800">
                                        <tr>
                                            <td width="800" valign="middle">
                                                <h1 style="font-family: arial; font-size: 17px; text-align: center;color: #ffffff;">{}</h1>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td width="1000" valign="top">
                                    <p>&nbsp;</p>
                                </td>
                            </tr>
                            <tr>
                                <td width="1000" valign="top">
                                    <table cellpadding="0" cellspacing="0" border="0" align="center" width="800">
                                        <tr>
                                            <td width="800" valign="top">
        """
        return tth + th.format(title)

    @staticmethod
    def _gen_html_end():

        htmlend = """
                                            <p style="font-size:13px; font-family:arial; color:#00b5c8; line-height: 18px; text-align:center;"></p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    <p>&nbsp;</p>
                                </td>
                           </tr>
                           <tr>
                                <td width="1000" valign="top" style="background-color:#00b5c8">
                                    <table cellpadding="0" cellspacing="0" border="0" align="center" width="800">
                                        <tr>
                                           <td width="200" valign="top" align="middle">
                                               <a href="https://www.sensetime.com">
                                                   <img src="https://www.sensetime.com/images/logo.png" alt="" width="85" style="width:85px;">
                                               </a>
                                           </td>
                                       </tr>
                                   </table>
                               </td>
                           </tr>
                       </table>
                       <!-- End example table -->
                   </td>
               </tr>
            </table>
            <!-- End of wrapper table -->
        </body>
        </html>"""
        return htmlend

    @staticmethod
    def gen_html_body(data_dict, head = None, title = None, head_color = None):
        html = ""
        #head
        if title:
            table_head = """
            <table id="t02" width="800" >
                <tr>
                    <th>{}</th>
                </tr {}>
            </table>
            """
            html += table_head.format(title, head_color)

        #table head
        html += """
        <table id="t01" width="800">
        """
        if head:
            table_html = """
                <tr>
                    {}
                </tr>
            """
            t = ""
            for tag in head:
                t += "<th>{}</th>".format(tag)
            html += table_html.format(t)

        #table data
        tmp = ""
        tmp += """<tr bgcolor="#f58500" align="center"><th>Key</th><th>Value</th></tr>"""
        for k, v in data_dict.items():
            tmp += """<tr bgcolor="#f2f3f2" align="center">"""
            tmp += '<td><font color="blue">{}</font></td>'.format(k)
            tmp += '<td><font color=blue">{}</font></td>'.format(v)
            tmp += "</tr>"
        html += tmp
        html += """</table>"""
        return html

    def gen_html(self, title, body):
        mail = "{}{}{}{}".format(
            self._gen_html_head(),
            self._gen_html_table_head(title),
            body,
            self._gen_html_end()
        )
        return mail


def main():
    mailer = MailService("http://127.0.0.1:6789/api/mail")
    body = mailer.gen_html_body("<h1>HelloWorld</h1>")
    html = mailer.gen_html("Process Alert By Supervisor".encode("utf-8"), body)
    mailer.send("zhoushuke@xxx.com", "Proceee Fires".encode("utf-8"), "html", html.encode("utf-8"))


if __name__ == '__main__':
    main()
