#!/usr/bin/env python
# vim: set fileencoding=utf-8

import re
import requests
import time

outputs = []
EXCHANGE_RATES = {}

MONEY_RE = r"(?i)(?P<amount>\d+(\.\d{1,2})?) ?(?P<currency>USD|GBP|EUR)"
MONEY_RE2 = u"(?P<currency>\$|\xa3|\u20ac)(?P<amount>\d+(\.\d{1,2})?)"

TEMP_RE = r"(?i)(?P<minus>(minus |-))?(?P<value>[0-9.]+) ?(degrees ?)?(?P<unit>C|F)"


def _get_exchange_rate(from_currency, to_currency):
    global EXCHANGE_RATES

    key = "{}-{}".format(from_currency, to_currency)
    print "fetching exchange rate", key
    try:
        when = EXCHANGE_RATES[key]['when']
    except:
        when = 0

    print "cache time", when
    now = time.time()
    if (now - when) > 86400:
        print "hitting API"
        r = requests.get("http://api.fixer.io/latest?base={}&symbols={}".format(from_currency, to_currency))
        # print "hit API"
        # print r
        if r.status_code != 200:
            print "Failed to hit fixer API"
            print r
            raise Exception("API error")
        rate = r.json()['rates'][to_currency]
        EXCHANGE_RATES[key] = {'rate': r.json()['rates'][to_currency], 'when': now}
    else:
        print "Using cached rate"
        rate = EXCHANGE_RATES[key]['rate']
    return rate


def process_message(data):
    line = data['text']
    channel = data['channel']
    if 'http' in line:
        print 'ignoring line with URL'
        return
    try:
        if time.time() - float(data['ts']) > 5:
            print 'message is too old'
            return
    except Exception as e:
        print e
        return
    matches = re.search(MONEY_RE, line)
    if matches:
        c = matches.group('currency').upper()
        a = float(matches.group('amount'))
        handle_currency(c, a, channel)
        return

    # print "checking 2nd form"
    try:
        matches = re.search(MONEY_RE2, line)
        if matches:
            # print "matches 2nd form"
            c = matches.group('currency')
            a = float(matches.group('amount'))
            if c == '$':
                c = 'USD'
            elif c == u'£':
                c = 'GBP'
            elif c == u'€':
                c = 'EUR'
            else:
                return
            try:
                handle_currency(c, a, data['channel'])
            except Exception, e:
                # print "cows"
                print e
            return
        matches = re.search(TEMP_RE, line)
        if matches:
            #print 'handling temp'
            unit = matches.group('unit')
            value = float(matches.group('value'))
            try:
                minus = matches.group('minus')
                if minus is not None and not minus == '':
                    value = 0 - value
            except:
            #    print 'e'
                pass
            new_value = None
            if unit in ['C', 'c']:
                new_value = value * 1.8 + 32
                old_unit = 'Celcius'
                new_unit = 'Fahrenheit'
            elif unit in ['F', 'g']:
                new_value = (value - 32) / 1.8
                old_unit = 'Fahrenheit'
                new_unit = 'Celcius'
            if new_value is not None:
                outputs.append([channel, u"{0:.1f} degrees {1} = {2:.1f} degrees {3}".format(value, old_unit, new_value, new_unit)])
                # print "output: temp"
                # print "input was:", data
                # TODO: emoji
            return
        #print 'nothing'
    except Exception, e:
        print e
        # print "moo"


def handle_currency(c, a, channel):
    try:
        if c == 'USD':
            try:
                rate = _get_exchange_rate('USD', 'GBP')
            except Exception, e:
                print e
                return
            retval = "{0:.2f} {1} == {2:.2f} {3}".format(
                a, c,
                a * rate, 'GBP')
            # print "output:", retval
            outputs.append([channel, retval])
        elif c == 'EUR':
            try:
                rate_gbp = _get_exchange_rate('EUR', 'GBP')
            except Exception, e:
                print e
                return
            try:
                rate_usd = _get_exchange_rate('EUR', 'USD')
            except Exception, e:
                print e
                return
            retval = "{0:.2f} {1} == {2:.2f} {3} == {4:.2f} {5}".format(
                a, c,
                a * rate_gbp, 'GBP',
                a * rate_usd, 'USD')
            # print "output:", retval
            outputs.append([channel, retval])
        elif c == 'GBP':
            try:
                rate = _get_exchange_rate('GBP', 'USD')
            except Exception, e:
                print e
                return
            retval = "{0:.2f} {1} == {2:.2f} {3}".format(
                a, c,
                a / rate, 'USD')
            # print "output:", retval
            outputs.append([channel, retval])
    except Exception, e:
        print "oh no"
        print e
