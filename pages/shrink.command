cd "$(dirname "$0")"
cd ./data
for i in *
do
if [ ! -d $i ]
then
continue
fi
cd $i
if [ -f ./banner.png ]
then
mkdir -p ../../out/$i
convert ./banner.png -resize 25% +dither -colors 256 -depth 8 ../../out/$i/mod_banner.png
pngout ../../out/$i/mod_banner.png
fi
if [ -f ./logo.png ]
then
mkdir -p ../../out/$i
convert ./logo.png -resize 25% +dither -colors 256 -depth 8 ../../out/$i/mod_logo.png
pngout ../../out/$i/mod_logo.png
fi
cd -
done