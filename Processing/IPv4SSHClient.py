from paramiko import SSHClient

import getpass
import socket
from errno import ECONNREFUSED, EHOSTUNREACH


from paramiko.config import SSH_PORT
from paramiko.py3compat import string_types
from paramiko.ssh_exception import (
    BadHostKeyException,
    NoValidConnectionsError,
)


from paramiko.transport import Transport
from paramiko.util import retry_on_signal, ClosingContextManager


class IPv4SSHClient(SSHClient):

    def connect(
        self,
        hostname,
        port=SSH_PORT,
        username=None,
        password=None,
        pkey=None,
        key_filename=None,
        timeout=None,
        allow_agent=True,
        look_for_keys=True,
        compress=False,
        sock=None,
        gss_auth=False,
        gss_kex=False,
        gss_deleg_creds=True,
        gss_host=None,
        banner_timeout=None,
        auth_timeout=None,
        gss_trust_dns=True,
        passphrase=None,
        disabled_algorithms=None,
    ):
        """
        Connect to an SSH server and authenticate to it.  The server's host key
        is checked against the system host keys (see `load_system_host_keys`)
        and any local host keys (`load_host_keys`).  If the server's hostname
        is not found in either set of host keys, the missing host key policy
        is used (see `set_missing_host_key_policy`).  The default policy is
        to reject the key and raise an `.SSHException`.

        Authentication is attempted in the following order of priority:

            - The ``pkey`` or ``key_filename`` passed in (if any)

              - ``key_filename`` may contain OpenSSH public certificate paths
                as well as regular private-key paths; when files ending in
                ``-cert.pub`` are found, they are assumed to match a private
                key, and both components will be loaded. (The private key
                itself does *not* need to be listed in ``key_filename`` for
                this to occur - *just* the certificate.)

            - Any key we can find through an SSH agent
            - Any "id_rsa", "id_dsa" or "id_ecdsa" key discoverable in
              ``~/.ssh/``

              - When OpenSSH-style public certificates exist that match an
                existing such private key (so e.g. one has ``id_rsa`` and
                ``id_rsa-cert.pub``) the certificate will be loaded alongside
                the private key and used for authentication.

            - Plain username/password auth, if a password was given

        If a private key requires a password to unlock it, and a password is
        passed in, that password will be used to attempt to unlock the key.

        :param str hostname: the server to connect to
        :param int port: the server port to connect to
        :param str username:
            the username to authenticate as (defaults to the current local
            username)
        :param str password:
            Used for password authentication; is also used for private key
            decryption if ``passphrase`` is not given.
        :param str passphrase:
            Used for decrypting private keys.
        :param .PKey pkey: an optional private key to use for authentication
        :param str key_filename:
            the filename, or list of filenames, of optional private key(s)
            and/or certs to try for authentication
        :param float timeout:
            an optional timeout (in seconds) for the TCP connect
        :param bool allow_agent:
            set to False to disable connecting to the SSH agent
        :param bool look_for_keys:
            set to False to disable searching for discoverable private key
            files in ``~/.ssh/``
        :param bool compress: set to True to turn on compression
        :param socket sock:
            an open socket or socket-like object (such as a `.Channel`) to use
            for communication to the target host
        :param bool gss_auth:
            ``True`` if you want to use GSS-API authentication
        :param bool gss_kex:
            Perform GSS-API Key Exchange and user authentication
        :param bool gss_deleg_creds: Delegate GSS-API client credentials or not
        :param str gss_host:
            The targets name in the kerberos database. default: hostname
        :param bool gss_trust_dns:
            Indicates whether or not the DNS is trusted to securely
            canonicalize the name of the host being connected to (default
            ``True``).
        :param float banner_timeout: an optional timeout (in seconds) to wait
            for the SSH banner to be presented.
        :param float auth_timeout: an optional timeout (in seconds) to wait for
            an authentication response.
        :param dict disabled_algorithms:
            an optional dict passed directly to `.Transport` and its keyword
            argument of the same name.

        :raises:
            `.BadHostKeyException` -- if the server's host key could not be
            verified
        :raises: `.AuthenticationException` -- if authentication failed
        :raises:
            `.SSHException` -- if there was any other error connecting or
            establishing an SSH session
        :raises socket.error: if a socket error occurred while connecting

        .. versionchanged:: 1.15
            Added the ``banner_timeout``, ``gss_auth``, ``gss_kex``,
            ``gss_deleg_creds`` and ``gss_host`` arguments.
        .. versionchanged:: 2.3
            Added the ``gss_trust_dns`` argument.
        .. versionchanged:: 2.4
            Added the ``passphrase`` argument.
        .. versionchanged:: 2.6
            Added the ``disabled_algorithms`` argument.
        """
        if not sock:
            errors = {}
            # Try multiple possible address families (e.g. IPv4 vs IPv6)
            to_try = list(self._families_and_addresses(hostname, port))
            for af, addr in to_try:
                if af == socket.AddressFamily.AF_INET6:
                    continue
                try:
                    sock = socket.socket(af, socket.SOCK_STREAM)
                    if timeout is not None:
                        try:
                            sock.settimeout(timeout)
                        except:
                            pass
                    retry_on_signal(lambda: sock.connect(addr))
                    # Break out of the loop on success
                    break
                except socket.error as e:
                    # Raise anything that isn't a straight up connection error
                    # (such as a resolution error)
                    if e.errno not in (ECONNREFUSED, EHOSTUNREACH):
                        raise
                    # Capture anything else so we know how the run looks once
                    # iteration is complete. Retain info about which attempt
                    # this was.
                    errors[addr] = e

            # Make sure we explode usefully if no address family attempts
            # succeeded. We've no way of knowing which error is the "right"
            # one, so we construct a hybrid exception containing all the real
            # ones, of a subclass that client code should still be watching for
            # (socket.error)
            if len(errors) == len(to_try):
                raise NoValidConnectionsError(errors)

        t = self._transport = Transport(
            sock,
            gss_kex=gss_kex,
            gss_deleg_creds=gss_deleg_creds,
            disabled_algorithms=disabled_algorithms,
        )
        t.use_compression(compress=compress)
        t.set_gss_host(
            # t.hostname may be None, but GSS-API requires a target name.
            # Therefore use hostname as fallback.
            gss_host=gss_host or hostname,
            trust_dns=gss_trust_dns,
            gssapi_requested=gss_auth or gss_kex,
        )
        if self._log_channel is not None:
            t.set_log_channel(self._log_channel)
        if banner_timeout is not None:
            t.banner_timeout = banner_timeout
        if auth_timeout is not None:
            t.auth_timeout = auth_timeout

        if port == SSH_PORT:
            server_hostkey_name = hostname
        else:
            server_hostkey_name = "[{}]:{}".format(hostname, port)
        our_server_keys = None

        our_server_keys = self._system_host_keys.get(server_hostkey_name)
        if our_server_keys is None:
            our_server_keys = self._host_keys.get(server_hostkey_name)
        if our_server_keys is not None:
            keytype = our_server_keys.keys()[0]
            sec_opts = t.get_security_options()
            other_types = [x for x in sec_opts.key_types if x != keytype]
            sec_opts.key_types = [keytype] + other_types

        t.start_client(timeout=timeout)

        # If GSS-API Key Exchange is performed we are not required to check the
        # host key, because the host is authenticated via GSS-API / SSPI as
        # well as our client.
        if not self._transport.gss_kex_used:
            server_key = t.get_remote_server_key()
            if our_server_keys is None:
                # will raise exception if the key is rejected
                self._policy.missing_host_key(
                    self, server_hostkey_name, server_key
                )
            else:
                our_key = our_server_keys.get(server_key.get_name())
                if our_key != server_key:
                    if our_key is None:
                        our_key = list(our_server_keys.values())[0]
                    raise BadHostKeyException(hostname, server_key, our_key)

        if username is None:
            username = getpass.getuser()

        if key_filename is None:
            key_filenames = []
        elif isinstance(key_filename, string_types):
            key_filenames = [key_filename]
        else:
            key_filenames = key_filename

        self._auth(
            username,
            password,
            pkey,
            key_filenames,
            allow_agent,
            look_for_keys,
            gss_auth,
            gss_kex,
            gss_deleg_creds,
            t.gss_host,
            passphrase,
        )