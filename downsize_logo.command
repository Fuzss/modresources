echo Drag-in logo file to compress...
read file
mogrify -resize 25% +dither -colors 256 -depth 8 $file
pngout $file