#!/bin/bash

# emerge options.
EMERGE_DEFAULT_OPTS="--quiet-build=y --nodeps --oneshot --usepkg" 

# short variable.
OPTS=$EMERGE_DEFAULT_OPTS

# list of packages to install.
packages="pam dnscrypt-proxy"

# add the temporary directory of the binaries. 
echo -e '\nPKGDIR="/installation/packages"' >> /etc/make.conf

# command to install the packages listed.
emerge $OPTS $packages

# remove the temporary directory line.
sed -i '/PKGDIR/d' /etc/make.conf

# find the remove line with nameserver.
sed -i '/name_servers/d' /etc/resolvconf.conf

# namserver configuration default file.
echo -e '\nname_servers=127.0.0.1' >> /etc/resolvconf.conf

# namserver configuration file.
echo 'nameserver 127.0.0.1' > /etc/resolv.conf

# enable dnscrypt-proxy service on default init.
rc-update add dnscrypt-proxy && rc-service dnscrypt-proxy start

# message.
echo -e "\n >>> Sucessfull Installed! \n"
