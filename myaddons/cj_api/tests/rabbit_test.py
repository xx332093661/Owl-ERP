# -*- coding: utf-8 -*-
import pika

# 正式库参数
username = 'admin'
password = 'colorful*2018'
ip = '10.0.0.24'
port = 5672

# # 测试库参数
# username = 'admin'
# password = 'colorful*2018'
# ip = '10.16.0.10'
# port = 5672


def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)

credentials = pika.PlainCredentials(username, password)
parameter = pika.ConnectionParameters(host=ip, port=port, credentials=credentials)
connection = pika.BlockingConnection(parameter)

queue_name = 'WMS-ERP-STOCK-QUEUE'
exchange = 'ERP_EXCHANGE'
channel = connection.channel()
channel.exchange_declare(exchange=exchange, exchange_type='topic', durable=True)
result = channel.queue_declare(queue=queue_name, exclusive=True, durable=True, passive=True)
channel.queue_bind(exchange=exchange, queue=queue_name)

channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()






