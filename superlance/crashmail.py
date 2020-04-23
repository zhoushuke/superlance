#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2007 Agendaless Consulting and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the BSD-like license at
# http://www.repoze.org/LICENSE.txt.  A copy of the license should accompany
# this distribution.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL
# EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND
# FITNESS FOR A PARTICULAR PURPOSE
#
##############################################################################

# A event listener meant to be subscribed to PROCESS_STATE_CHANGE
# events.  It will send mail when processes that are children of
# supervisord transition unexpectedly to the EXITED state.

# A supervisor config snippet that tells supervisor to use this script
# as a listener is below.
#
# [eventlistener:crashmail]
# command =
#     /usr/bin/crashmail
#         -o hostname -a -e public -m notify-on-crash@domain.com
#         -s '/usr/sbin/sendmail -t -i -f crash-notifier@domain.com'
# events=PROCESS_STATE
#
# Sendmail is used explicitly here so that we can specify the 'from' address.

doc = """\
crashmail.py [-p processname] [-a] [-e environment] [-o string] [-t mail_address_to]
             [-f mail_address_from] 

Options:

-p -- specify a supervisor process_name.  Send mail when this process
      transitions to the EXITED state unexpectedly. If this process is
      part of a group, it can be specified using the
      'group_name:process_name' syntax.

-a -- Send mail when any child of the supervisord transitions
      unexpectedly to the EXITED state unexpectedly.  Overrides any -p
      parameters passed in the same crashmail process invocation.

-e -- Specify a flag to mark the environment, like test, production, poc...etc

-o -- Specify a parameter used as a prefix in the mail subject header.

-f -- specify an email server RESTful  to use to send email
      (e.g. "http://127.0.0.1:6789/api/mail").  Must be a command which 
      accepts header and message data on stdin and sends mail.  Default is
      "http://127.0.0.1:6789/api/mail".

-t -- specify an email address.  The script will send mail to this
      address when crashmail detects a process crash.  If no email
      address is specified, email will not be sent.

The -p option may be specified more than once, allowing for
specification of multiple processes.  Specifying -a overrides any
selection of -p.

A sample invocation:

crashmail.py -p program1 -p group1:program2 -f email_from@example.com -t email_to@example.com

"""

import getopt
import os
import sys
import socket
import collections
from sendxmail import MailService
from supervisor import childutils


def usage(exitstatus=255):
    print(doc)
    sys.exit(exitstatus)


class CrashMail:

    def __init__(self, programs, any, envi, email_host, email_to, optionalheader):

        self.programs = programs
        self.any = any
        self.envi = envi
        self.email_host = email_host
        self.email_to = email_to
        self.optionalheader = optionalheader
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.mailer = MailService(self.email_host)

    @staticmethod
    def get_host_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip

    def runforever(self, test = False):
        while 1:
            # we explicitly use self.stdin, self.stdout, and self.stderr
            # instead of sys.* so we can unit test this code
            headers, payload = childutils.listener.wait(
                self.stdin, self.stdout)

            if not headers['eventname'] == 'PROCESS_STATE_EXITED':
                # do nothing with non-TICK events
                childutils.listener.ok(self.stdout)
                if test:
                    self.stderr.write('non-exited event\n')
                    self.stderr.flush()
                    break
                continue

            pheaders, pdata = childutils.eventdata(payload+'\n')

            if int(pheaders['expected']):
                childutils.listener.ok(self.stdout)
                if test:
                    self.stderr.write('expected exit\n')
                    self.stderr.flush()
                    break
                continue

            # event timestamp
            event_timestamp = childutils.get_asctime()

            #get local ip:
            host_ip = self.get_host_ip()

            #process name
            process_name = pheaders['processname']

            #process pid
            process_pid = pheaders['pid']

            #group name
            group_name = pheaders['groupname']

            #from_state
            from_state = pheaders['from_state']

            #msg
            msg = 'Process %s in group %s EXITED unexpectedly (pid %s) from state %s' % (process_name,
                                                                                         group_name,
                                                                                         process_pid,
                                                                                         from_state)
            #html struct
            html_struct = collections.OrderedDict()
            html_struct['event_time'] = event_timestamp
            html_struct['environment'] = self.envi
            html_struct['host_ip'] = host_ip
            html_struct['process_name'] = process_name
            html_struct['process_pid'] = process_pid
            html_struct['event_msg'] = msg

            #subject
            subject = '%s in %s crashed at %s' % (process_name,
                                                  host_ip,
                                                  event_timestamp)

            if self.optionalheader:
                subject = self.optionalheader + ':' + subject

            self.stderr.write('unexpected exit, mailing\n')
            self.stderr.flush()

            #self.mail(self.email_to, subject, msg)
            self.send_mail_by_http(self.email_to, subject, html_struct)

            childutils.listener.ok(self.stdout)
            if test:
                break

    def mail(self, email_to, subject, msg):
        body = 'To: %s\n' % email_to
        body += 'Subject: %s\n' % subject
        body += '\n'
        body += msg
        with os.popen(self.sendmail, 'w') as m:
            m.write(body)
        self.stderr.write('Mailed:\n\n%s' % body)
        self.mailed = body

    def send_mail_by_http(self, email_to, subject, html_content):
        body = self.mailer.gen_html_body(html_content)
        html = self.mailer.gen_html('Process Alert By Supervisor'.encode('utf-8'), body)
        self.mailer.send(email_to, subject.encode('utf-8'), 'html', html.encode('utf-8'))


def main(argv=sys.argv):
    short_args = "hp:ae:o:f:t:"
    long_args = [
        "help",
        "program=",
        "any",
        "envi=",
        "optionalheader=",
        "from_email=",
        "to_email=",
        ]
    arguments = argv[1:]
    try:
        opts, args = getopt.getopt(arguments, short_args, long_args)
    except Exception:
        usage()

    programs = []
    any = False
    envi = 'PublicCloud'
    from_email = 'https://senserealty.sensetime.com/xa2xwd3f6Idy/api/mail'
    to_email = 'senserealty_devops@sensetime.com'
    optionalheader = None

    for option, value in opts:

        if option in ('-h', '--help'):
            usage(exitstatus=0)

        if option in ('-p', '--program'):
            programs.append(value)

        if option in ('-a', '--any'):
            any = True

        if option in ('-e', '--envi'):
            envi = value

        if option in ('-f', '--from_email'):
            from_email = value

        if option in ('-t', '--to_email'):
            to_email = value

        if option in ('-o', '--optionalheader'):
            optionalheader = value

    if not 'SUPERVISOR_SERVER_URL' in os.environ:
        sys.stderr.write('crashmail must be run as a supervisor event'
                         'listener\n')
        sys.stderr.flush()
        return

    prog = CrashMail(programs, any, envi, from_email, to_email, optionalheader)
    prog.runforever()


if __name__ == '__main__':
    main()

