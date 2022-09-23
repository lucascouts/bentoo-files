#!/bin/bash 

function flatpack_add_flathub() {

	flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

}


flatpack_add_flathub()