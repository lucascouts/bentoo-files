#!/bin/bash

# emerge options.
EMERGE_DEFAULT_OPTS="--quiet-build=y --nodeps --oneshot --usepkg -j9"

# short variable.
OPTS=$EMERGE_DEFAULT_OPTS

# list of packages to install.
packages="pam dnscrypt-proxy"

# add the temporary directory of the binaries.
echo -e '\nPKGDIR="/installation/packages"' >> /etc/portage/make.conf

# command to install the packages listed.
FEATURES="-getbinpkg" emerge $OPTS $packages

# remove the temporary directory line.
sed -i '/PKGDIR/d' /etc/portage/make.conf

# namserver configuration default file.
echo -e 'resolv_conf=/etc/resolv.conf\nname_servers=127.0.0.1' > /etc/resolvconf.conf

# namserver configuration file.
echo 'nameserver 127.0.0.1' > /etc/resolv.conf

# enable dnscrypt-proxy service on default init.
rc-update add dnscrypt-proxy default && rc-service dnscrypt-proxy start

# update env
env-update && source /etc/profile