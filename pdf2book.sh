#!/bin/sh

function input_page_file {
    printf "input-%02g.ppm" $*
}

function single_page_file {
    printf "single-%03g.ppm" $*
}

function output_page_file {
    printf "output-%03g.ppm" $*
}

rotate_angle=0 # 90
mode="" # "single"
skip_page=""

input=$1
output=$2

pdftoppm $input ./input
opages=`ls -1 input-*.ppm | wc -l`
olast=$opages
echo "original pages number $opages"

if [[ $mode == "" ]]; then
    if [[ $(( (opages * 2) % 4 )) -eq 0 ]]; then
        mode="firstDouble"
    else
        mode="firstSingle"
    fi
fi
echo "mode $mode"

if [[ $mode == "firstSingle" ]]; then
    start=2
    stop=$((olast - 1))
    step=1
    k=2
    mv `input_page_file 1` `single_page_file 1`
    mv `input_page_file $olast` `single_page_file $pages`
    pages=2
elif [[ $mode == "firstDouble" ]]; then
    start=1
    stop=$olast
    step=1
    k=0
    pages=0
elif [[ $mode == "single" ]]; then
    start=1
    stop=$olast
    step=1
    k=1
    pages=0
fi

echo "split from $start to $stop, step $step"

pages=0
for i in `seq $start $step $stop`; do
    input_page=`input_page_file $i`

    if echo $skip_page | grep -w $i >/dev/null ; then
        continue
    fi

    if [[ $mode == "firstSingle" || $mode == "firstDouble" ]]; then
        convert -crop 50%x100% "${input_page}" tmp-%d.ppm
        mv tmp-0.ppm `single_page_file $k`
        mv tmp-1.ppm `single_page_file $((k+1))`
        k=$((k+2))
        pages=$((pages+2))
    elif [[ $mode == "single" ]]; then
        convert -rotate ${rotate_angle} "${input_page}" `single_page_file $k`
        k=$((k+1))
        pages=$((pages+1))
    fi

    rm "${input_page}"
done

if [[ $mode == "firstDouble" ]]; then
    mv `single_page_file 0` `single_page_file $k`
    k=$((k+1))
fi

echo "pages $pages"

blank=$(((4 - (pages % 4)) % 4))
echo "number of blank pages to add $blank"

echo "rearrange pages"
i=1
j=$((pages + blank))
k=0
while [[ $i -lt $j ]]; do
    if [[ $j -gt $pages ]]; then
        convert -fill 'rgb(255,255,255)' -colorize 100,100,100 `single_page_file $i` `single_page_file $j`
    fi
    if [[ $((i % 2)) -eq 1 ]]; then
        montage `single_page_file $j` `single_page_file $i` -geometry +0+0 `output_page_file $k`
    else
        montage `single_page_file $i` `single_page_file $j` -geometry +0+0 `output_page_file $k`
    fi
    k=$((k + 1))
    i=$((i+1))
    j=$((j-1))
done

echo "convert to pdf"
convert output-*.ppm $output

echo "rm ppm"
rm *.ppm
