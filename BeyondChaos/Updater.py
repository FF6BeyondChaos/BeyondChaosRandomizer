#!/usr/bin/env python3
import requests


def update():
    x = requests.get('https://google.com/')
    print(x.text)