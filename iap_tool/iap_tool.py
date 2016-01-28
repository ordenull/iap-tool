#!/usr/bin/env python
'''
A helper tool to work with Apple's App Store in-app-purchase receipts.
Copyright (C) 2013 Stan Borbat <stan@borbat.com>
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import sys
import argparse
import requests
import json
import os
from collections import OrderedDict
from datetime import datetime

# Apple receipt validation error codes
apple_error_codes = dict()
apple_error_codes[21000] = 'The App Store could not read the JSON object you provided.'
apple_error_codes[21002] = 'The data in the receipt-data property was malformed or missing.'
apple_error_codes[21003] = 'The receipt could not be authenticated.'
apple_error_codes[21004] = 'The shared secret you provided does not match the shared secret on file for your account.'
apple_error_codes[21005] = 'The receipt server is not currently available.'
apple_error_codes[21006] = 'This receipt is valid but the subscription has expired. When this status code is returned to your server, the receipt data is also decoded and returned as part of the response.'
apple_error_codes[21007] = 'This receipt is from the test environment, but it was sent to the production environment for verification. Send it to the test environment instead.'
apple_error_codes[21008] = 'This receipt is from the production environment, but it was sent to the test environment for verification. Send it to the production environment instead.'

def main():
  """ This is the main entry point for the program """
  parser = argparse.ArgumentParser(description='A command line AppStore receipt verifier with a web based GUI')
  parser.add_argument('receipt', help='Receipt Data', nargs='?', default='')
  parser.add_argument('--secret', type=str, nargs=1, metavar=('<key>'), help='The secret app-key to use')
  parser.add_argument('--sandbox', help='Use the sandbox', action="store_true")
  parser.add_argument('--dump', help='Print the full result, as opposed to only a summary', action="store_true")
  parser.add_argument('--webserver', type=int, nargs=1, metavar=('<port>'), help='Starts a web based user interface on <port>')
  parser.add_argument('--badapple', type=int, nargs=1, metavar=('<port>'), help='Starts a faulty AppStore receipt verification server on <port>')
  args = parser.parse_args()
  secret = args.secret[0] if args.secret is not None else None

  if args.webserver is not None:
    start_webserver(port=args.webserver[0])
    exit(0)

  if args.badapple is not None:
    start_badapple(port=args.badapple[0])
    exit(0)

  if len(args.receipt) == 0:
      parser.print_help()
      exit(0)

  # Non-interactive invocation
  error, json_data = validate(args.receipt, 
                              secret=secret,
                              sandbox=args.sandbox)
  if error is not None:
    print error
    exit(1)
  else:
    summary = generate_summary(json_data, technical=True)
    json_data.pop('latest_receipt')
    print "================================ Receipt Summary ==============================="
    max_length = len(max(summary, key=len))
    for name, value in summary.iteritems():
      print '{0}: {1}'.format(name.ljust(max_length+1), value)
    if args.dump:
      print "=============================== JSON Receipt Data =============================="
      print json.dumps(json_data, sort_keys=True, indent=4, separators=(',', ': '))
    exit(0)


def date_from_ms(timestamp):
  """ Convert the a timestamp from milliseconds to seconds 
  Args:
      timestamp: a timestamp in milliseconds
  """
  return int(timestamp) / 1000


def date_to_friendly(timestamp):
  """ Converts a timestamp from unix time (in seconds) to a readable string
  For example "2 days ago" if the date is in the past, or "in 2 days" if
  the date is in the future.
  Args:
      timestamp: a unix timestamp in seconds
  """
  then = datetime.fromtimestamp(timestamp)
  now = datetime.now()
  interval = then - now
  sec = interval.seconds
  days = interval.days
  minutes = interval.min
  total_sec = interval.total_seconds()
  if abs(interval.days) >= 1:
    days = interval.days
    return "in {0} days".format(days) if then>now else "{0} days ago".format(abs(days))
  if abs(interval.seconds) > (60*60):
    hours = interval.seconds / (60*60)
    return "in {0} hours".format(hours) if then>now else "{0} hours ago".format(abs(hours))
  if abs(interval.seconds) > 60:
    seconds = interval.seconds
    return "in {0} hours".format(seconds) if then>now else "{0} seconds ago".format(abs(seconds))


def validate(receipt, secret=None, sandbox=False):
  """ Validate the purchase receipt with Apple and get back a json response with
  the contents of the receipt. Subscription receipts require the private app key
  Args:
      receipt: iTunes purchase receipt data encoded in base64
      secret: the secret app key required to check subscription receipts
      sandbox: set to True if the receipt is from the sandbox environment
  Yield:
      A touple consisting of (error, result), if successful the error is None
      and the result is a dictionary. In case of an error the error is a string
      describing the error and the result is None.
  """
  error, result = None, None
  uri = "https://sandbox.itunes.apple.com/verifyReceipt" if sandbox \
    else "https://buy.itunes.apple.com/verifyReceipt"

  # Prepare the outgoing request
  request_payload = dict()
  request_payload['receipt-data'] = receipt
  if secret is not None:
    request_payload['password'] = secret

  # Send out the request
  try:
    response = requests.post(uri, json.dumps(request_payload), verify=False)
  except:
    error = "Network error while sending the request"
    return error, result

  # Make sure that Apple's server returned an HTTP OK response
  if response.status_code != 200:
    error = "The server wasn't able to process your request and returned an HTTP code {0}".format(response.status_code)
    return error, result

  # Try to parse the response as JSON
  try:
    result = json.loads(response.content)
  except:
    error = "Couldn't parse JSON data"
    return error, result

  # Does it have a valid status code?
  if not result.has_key('status'):
    error = "Couldn't find a status code in the JSON response"
    return error, response

  # Is the status code a number?
  try:
    status = int(result['status'])
  except:
    error = "The status code wasn't a number, it was: {0}".format(result['status'])

  # See if the status code is a happy one
  if status != 0:
    # Error received from Apple; Try to make sense of it
    if apple_error_codes.has_key(status):
      error = apple_error_codes[status]
    else:
      error = "Unknown Apple error code received: {0}".format(status)
    return error, result

  # We have made it this far, Apple returned a valid JSON object with a zero status code
  return error, result


def generate_summary(json_data, technical=True):
  """ Generate and return key-value summary of the receipt data.
  Args:
      json_data: the JSON receipt object returned from Apple
      technical: setting this to False will result in only 
                 non-technical output.
  """
  if json_data is None or json_data['status'] != 0:
    return None
  summary = OrderedDict()
  
  # Find the origional purchase receipt
  original_recept = None
  for receipt in json_data['receipt']['in_app']:
    if original_recept is None:
      original_recept = receipt
    else:
      if receipt['transaction_id'] == receipt['original_transaction_id']:
        if original_recept is not None:
          summary['Warning'] = 'Multiple in-app receipts found with the original transaction id'
        original_recept = receipt

  # Find the latest renewal receipt
  latest_receipt = None
  for receipt in json_data['latest_receipt_info']:
    if latest_receipt is None:
      latest_receipt = receipt
    else:
      if receipt['expires_date_ms'] > latest_receipt['expires_date_ms']:
        latest_receipt = receipt

  if technical:
    summary['Bundle ID'] = json_data['receipt']['bundle_id']
    # Origional in-app purchase
    summary['Original transaction ID'] = original_recept['transaction_id']
    summary['Original product ID'] = original_recept['product_id']
    summary['Original purchase date (UTC)'] = original_recept['purchase_date']
    summary['Original purchase date (Unix)'] = date_from_ms(original_recept['purchase_date_ms'])
    # Latest subscription info (controlled outside of the app
    summary['Latest transaction ID'] = latest_receipt['transaction_id']
    summary['Latest product ID'] = latest_receipt['product_id']
    summary['Latest purchase Date (UTC)'] = latest_receipt['purchase_date']
    summary['Latest purchase Date (Unix)'] = date_from_ms(latest_receipt['purchase_date_ms'])
    # Ultimate subscription date
    summary['Expiration (UTC)'] = latest_receipt['expires_date']
    summary['Expiration (Unix)'] = date_from_ms(latest_receipt['expires_date_ms'])
    summary['Subscription Expires'] = date_to_friendly(date_from_ms(latest_receipt['expires_date_ms']))
  else:
    if original_recept['product_id'] != latest_receipt['product_id']:      
      summary['Original product ID'] = original_recept['product_id']
      summary['Latest product ID'] = latest_receipt['product_id']
    else:
      summary['Product ID'] = latest_receipt['product_id']
    summary['Subscription Expires'] = date_to_friendly(date_from_ms(latest_receipt['expires_date_ms']))
    
  return summary


def start_webserver(port=8080):
  """ Start the webserver that displays the user interface.
  Args:
      port: port number to listen on
  """
  from bottle import get, post, request, response, run

  def parse_input(request, response):
    """ Processes all of the webapp parameters, saving some of them as cookies
    Args:
        request: bottle web request object
        response: bottle web response object
    """
    # First get any cookie values if they are set, otherwise defaults
    secret = request.get_cookie('secret', default='')
    sandbox = request.get_cookie('sandbox', default='no')
    externals = request.get_cookie('externals', default='yes')
    technical = request.get_cookie('technical', default='yes')

    secret = request.forms.get('secret', default=secret)
    # If it's a post request then we have to process the checkboxes
    # their value is empty if they aren't checked and 'yes' they are
    if request.method == 'POST':
      sandbox = request.forms.get('sandbox', default='no')
      externals = request.forms.get('externals', default='no')
      technical = request.forms.get('technical', default='no')
    # No cookie for storing receipts so the default is declared here
    receipt = request.forms.get('receipt', default='') # Text area

    # Sanitize the input here
    secret = secret.strip()
    sandbox = True if sandbox == 'yes' else False
    externals = True if externals == 'yes' else False
    technical = True if technical == 'yes' else False

    # Finally export all of the current values as cookies
    response.set_cookie('secret', secret, max_age=60*60*24*30)
    response.set_cookie('sandbox', 'yes' if sandbox else 'no', max_age=60*60*24*30)
    response.set_cookie('externals', 'yes' if externals else 'no', max_age=60*60*24*30)
    response.set_cookie('technical', 'yes' if technical else 'no', max_age=60*60*24*30)

    return secret, sandbox, externals, technical, receipt

  @get('/')
  def forms():
    """ Processes GET requests to the AppStore receipts form """
    secret, sandbox, externals, technical, receipt = parse_input(request, response)
    return template(secret=secret,
                    sandbox=sandbox,
                    externals=externals,
                    technical=technical)

  @post('/')
  def check():
    """ Processes POST requests to the AppStore receipts form """
    secret, sandbox, externals, technical, receipt = parse_input(request, response)
    error, json_data = validate(receipt, secret, sandbox)
    summary = generate_summary(json_data, technical)
    return template(secret=secret,
                    sandbox=sandbox,
                    externals=externals,
                    technical=technical,
                    summary=summary,
                    json_data=json_data,
                    error=error)

  def template(secret='',
               sandbox=False,
               externals=False,
               technical=False,
               summary=None,
               json_data=None,
               error=None):
    """ Return the page HTML code
    This is a minimalistic template engine that's responsible for all pages.
    It's embedded like this to keep the whole program contained as a single file
    Args:
        secret: value for the secret field
        sandbox: enable the sandbox checkbox
        externals: enable the external checkbox
        technical: enable the technical checkbox
        summary: summary dictionary or None
        json_data: receipt dictionary or None
        error: error mesasge or None
    """
    out = '<!DOCTYPE html>'
    out += '<html>'
    out += '<head>'
    if externals:
      out += '<link rel="stylesheet" title="Default" href="https://highlightjs.org/static/demo/styles/default.css">'
      out += '<script src="https://code.jquery.com/jquery-2.1.3.min.js"></script>'
      out += '<script src="https://highlightjs.org/static/highlight.pack.js"></script>'
      out += '<script>hljs.initHighlightingOnLoad();</script>'
      #out += '<script src="https://code.jquery.com/jquery-2.1.3.min.js"></script>'
      #out += '<script src="https://raw.githubusercontent.com/isagalaev/highlight.js/master/src/highlight.js"></script>'
      #out += '<script>hljs.initHighlightingOnLoad();</script>'
      #out += '<link rel="stylesheet" title="Default" href="https://raw.githubusercontent.com/isagalaev/highlight.js/master/src/styles/default.css">'
    out += '</head>'
    out += '<body>'
    out += '<form action="/" method="post">'

    out += '<fieldset>'
    out += '  <legend>App Store Parameters</legend>'
    out += '  <table>'
    
    # App key required for subscription receipts
    out += '    <tr>'
    out += '      <td><label for="secret">App Key (secret):</label></td>'
    out += '      <td><input name="secret" type="text" placeholder="app store hash" value="{0}" /></td>'.format(secret)
    out += '    </tr>'
    
    # Use Apple's sandbox environment
    out += '    <tr>'
    out += '      <td><label for="sandbox">Sandbox:</label></td>'
    if sandbox:
      out += '      <td><input type="checkbox" name="sandbox" value="yes" checked />'
    else:
      out += '      <td><input type="checkbox" name="sandbox" value="yes" />'
    out += '    </tr>'
    
    # Use external HTTP resources
    out += '    <tr>'
    out += '      <td><label for="externals">Externals:</label></td>'
    if externals:
      out += '      <td><input type="checkbox" name="externals" value="yes" checked />'
    else:
      out += '      <td><input type="checkbox" name="externals" value="yes" />'
    out += '    </tr>'

    # Show technical output
    out += '    <tr>'
    out += '      <td><label for="externals">Technical output:</label></td>'
    if technical:
      out += '      <td><input type="checkbox" name="technical" value="yes" checked />'
    else:
      out += '      <td><input type="checkbox" name="technical" value="yes" />'
    out += '    </tr>'

    out += '  </table>'
    out += '</fieldset>'

    out += '<fieldset>'
    out += '  <legend>Receipt</legend>'
    if error is None and json_data is not None:
      out += '  <textarea name="receipt" wrap="soft" placeholder="base64 encoded receipt" rows="10" style="width: 99%;" autofocus>{0}</textarea>'.format(json_data['latest_receipt'])
      json_data.pop('latest_receipt')
    else:
      out += '  <textarea name="receipt" wrap="soft" placeholder="base64 encoded receipt" rows="10" style="width: 99%;" autofocus></textarea>'
    out += '</fieldset>'
    out += '<input name="validate" type="submit" value="Validate" style="width: 100%; margin-top: 8px; margin-bottom: 20px; height: 30px;"/>'
    out += '</form>'

    if error is not None:
      out += '<fieldset>'
      out += '  <legend>Error</legend>'
      out += '  <p style="color: red"><strong>'
      out +=      error
      out += '  </strong></p>'
      out += '</fieldset>'
    elif summary is not None:
      # Summary
      out += '<fieldset>'
      out += '  <legend>Summary</legend>'
      out += '  <table>'
      for key, value in summary.iteritems():
        out += '    <tr><td>{0}:</td><td>{1}</td><tr>'.format(key, value)
      out += '  </table>'
      out += '</fieldset>'
  
      # Raw response
      if technical:
        out += '<fieldset>'
        out += '  <legend>Receipt</legend>'
        out += '  <pre><code class="hljs">'
        out +=      json.dumps(json_data, sort_keys=True, indent=4, separators=(',', ': '))
        out += '  </code></pre>'
        out += '</fieldset>'
  
      out += '</body>'
      out += '</html>'
    return out
  
  run(host='localhost', port=port, debug=True)


def start_badapple(port=80):
  """ Starts a faultly AppStore receipt verification server that will
  somtimes disconnect, return unexpected HTTP codes, malformed JSON and
  random Apple response codes.
  Args:
      port: port number to listen on
  """
  from bottle import post, response, run
  import random

  @post('/verifyReceipt')
  def valishate():
    """ Processes POST a receipt validation in a terrible way """
    # Flip a coin, if it's heads return a 200 response otherwise another code
    response_code = 200 if random.choice([True,False]) else random.choice([304, 404, 500])
    
    # Flip a coin, should we return a garbage response body?
    if random.choice([True, False]):
      response_body = '{I [you}'
    else:
      # Choose an error response code to return with valid JSON
      apple_code = random.choice(apple_error_codes.keys())
      response_dict = {'status': apple_code}
      response_body = json.dumps(response_dict)

    response.status = response_code
    return response_body

  run(host='localhost', port=port, debug=True)


if __name__ ==  "__main__":
  main()
