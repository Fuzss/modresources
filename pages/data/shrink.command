cd "$(dirname "$0")"
for i in *
do
if [ ! -d $i ]
then
continue
fi
cd $i
if [ -f ./banner.png ]
then
convert ./banner.png -resize 25% +dither -colors 256 -depth 8 ./mod_banner.png
fi
if [ -f ./logo.png ]
then
convert ./logo.png -resize 25% +dither -colors 256 -depth 8 ./mod_logo.png
fi
cd -
done