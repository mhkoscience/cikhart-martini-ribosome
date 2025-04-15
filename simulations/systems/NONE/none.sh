for d in ch_*; do
    if [ -d "$d" ]; then
        sed -i 's/#define RUBBER_FC 500\.000000/#define RUBBER_FC 0\.000000/g' "$d"/*.itp
    fi
done
