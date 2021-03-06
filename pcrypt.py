import getopt
import getpass
import json
import lib.gnupg
import lib.server
import os
import socket
import sys
import textwrap

def usage():
    str = '''
        Usage:
        Optional flags:
            -c, --config      A config file that the script will read to get remote system information. Session will be non-interactive.
                              Useful for automation.
            -d, --decrypt     Signals the specified operation should be decryption rather than the default encryption.
            -f, --file        The file to encrypt/decrypt.
            -o, --output      The name of the new file (will create first if it doesn't exist).
            -r, --recipients  A comma-separated string of recipients.
            -s, --sign        The user ID with which to sign the encrypted file.
            -h, --help        Help.
    '''
    print(textwrap.dedent(str))

def main(argv):
    json = None
    decrypt = False
    filename = ''
    output = None
    recipients = None
    sign = None

    try:
        opts, args = getopt.getopt(argv, 'hdc:f:o:r:s:', ['help', 'decrypt', 'config=', 'file=', 'output=', 'recipients=', 'sign='])
    except getopt.GetoptError:
        print('Error: Unrecognized function argument.')
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '-help', '--help'):
            usage()
            sys.exit(0)
        elif opt in ('-d', '--decrypt'):
            decrypt = True
        elif opt in ('-f', '--file'):
            filename = arg
        elif opt in ('-o', '--output'):
            output = arg
        elif opt in ('-r', '--recipients'):
            recipients = arg
        elif opt in ('-s', '--sign'):
            sign = arg
        elif opt in ('-c', '--config'):
            json = arg

    if (filename):
        if not decrypt:
            encrypt_file(filename, output=output, recipients=recipients, sign=sign, json=json)
        else:
            decrypt_file(filename, output)
    else:
        print('Error: No file given.')
        sys.exit(1)

def decrypt_file(filename, output):
    gpg = _setup()

    try:
        if not output:
            output = input('Name of outputted decrypted file: ')

        passphrase = _get_passphrase()

        with open(filename, 'rb') as f:
            decrypted = gpg.decrypt_file(f, passphrase=passphrase, output=output)

        if decrypted.ok:
            print('File decryption successful.')

            _maybe_remove_file(filename, output)
            sys.exit(0)
        else:
            #print('Error: ' + decrypted.stderr)
            print('Bad passphrase!')
            sys.exit(1)

    except (KeyboardInterrupt, EOFError):
        _abort()

def encrypt_file(filename, **kwargs):
    output = kwargs.get('output')
    if not output:
        output = input('Name of outputted encrypted file: ')

    recipients = kwargs.get('recipients')
    if not recipients:
        recipients = 'benjam72@yahoo.com'

    sign = kwargs.get('sign')
    if not sign:
        sign = 'benjam72@yahoo.com'

    json = kwargs.get('json')

    gpg = _setup()

    passphrase = _get_passphrase()

    with open(filename, 'rb') as f:
        encrypted = gpg.encrypt_file(f, [recipients], sign=sign, passphrase=passphrase, output=output)

    if encrypted.ok:
        print('File encryption successful.')

        if json:
            try:
                # This can read 'username hostname port'.
                # username, hostname, port = open(arg, encoding='utf-8').readline().split()

                # TODO: Is there a better way to get the values from the Json?
                with open(json, mode='r', encoding='utf-8') as f:
                    json_data = json.loads(f.read())

                username = json_data.get('username')
                hostname = json_data.get('hostname')
                port = str(json_data.get('port'))

            # Exceptions could be bad Json or file not found.
            except (ValueError, FileNotFoundError) as e:
                print(e)
                sys.exit(1)

            lib.server.put(output, hostname, username, port, destination)
        else:
            # Establish default values.
            destination = '~'
            hostname = socket.gethostname()
            port = '80'
            username = getpass.getuser()

            # Push to server.
            lib.server.prepare(output)

        _maybe_remove_file(filename, output)
        sys.exit(0)
    else:
        print('Error: ' + encrypted.stderr)
        sys.exit(1)

def _abort():
    # Control-C or Control-D sent a SIGINT to the process, handle it.
    print('\nProcess aborted!')
    sys.exit(1)

def _get_passphrase():
    try:
        return getpass.getpass('Enter your passphrase: ')

    except (KeyboardInterrupt, EOFError):
        _abort()

def _maybe_remove_file(filename, output):
    # Only offer to remove original file if not editing in place!
    if output != filename:
        resp = input('Remove original file? [y|N]: ')
        if resp in ['Y', 'y']:
            os.remove(filename)

def _setup():
    return lib.gnupg.GPG(gnupghome=os.getenv('CRYPT_GNUPGHOME', '/Users/btoll/.gnupg'), gpgbinary=os.getenv('CRYPT_GPGBINARY', 'gpg'))

if __name__ == '__main__':
    if (len(sys.argv) > 1):
        main(sys.argv[1:])
    else:
        usage()
        sys.exit(0)

