#!/bin/sh

WORKDIR=".."
WORKDIR=$(cd ${WORKDIR} && pwd)

VERSION="$(cat VERSION 2>/dev/null)"

DATE="$(date '+%Y%m%d-%H%M%S')"
PROJECTNAME=$(basename $(pwd))
echo "--- backup $PROJECTNAME Ver. ${VERSION}"

BACKUPDIR="${WORKDIR}/${PROJECTNAME}-backup"
BACKUPNAME="${PROJECTNAME}-${VERSION}-src-${DATE}"
mkdir -p "${BACKUPDIR}" | exit 1

TMPDIR="${WORKDIR}/${BACKUPNAME}"
mkdir -p "${TMPDIR}" | exit 1
cp -r . "${TMPDIR}" | exit 1

#cmd="zip -r -q -9 ${BACKUPDIR}/${BACKUPNAME}.zip ${BACKUPNAME}"
cmd="7z a -mx9 ${BACKUPDIR}/${BACKUPNAME}.7z ${BACKUPNAME}"
echo "$cmd"

(cd $WORKDIR && $cmd)
[ $? -ne 0 ] && exit 1

rm -rf ${TMPDIR} #1>/dev/null

echo ""
(cd $BACKUPDIR && pwd && ls -la ${BACKUPNAME}.zip)
echo ""

