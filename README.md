# iap-tool
A helper tool to work with Apple's App Store in-app-purchase receipts.

##Usage

There are three ways to use this tool, as a console app, a web-app and as a purposely faulty Apple server.

### Command line parameters

#### Positional parameters
  * <receipt> *- A full base64 encoded Apple Store purhase receipt **[OPTIONAL]***

#### General parameters
  * --secret *- The App Store secret that is required to check subscription receipts*
  * --sandbox *- Sandbox mode*
  * --dump *- Print the full result, as opposed to only a summary*
  * --webserver <port> *- Starts a web based user interface on specified port*
  * --badapple <port> *- Starts a faulty AppStore receipt verification service on specified port*

##Copyright and License

Copyright (C) 2016 [Stan Borbat](http://stan.borbat.com)

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
