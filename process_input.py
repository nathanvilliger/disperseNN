# helper utils for processing empirical input data

import os
import numpy as np
from read_input import *
import sys
from geopy import distance


# project locations from ellipsoid (lat,long) to square (km)
def project_locs(coords,precision):

    # find min/max lat and long
    coords = np.array(coords)
    #coords[:,0] *= -1 # for testing southern hemisphere
    min_lat = min(coords[:,0])
    max_lat = max(coords[:,0])
    min_long = min(coords[:,1])
    max_long = max(coords[:,1])

    # quick check to make sure the samples don't span over 180 degress
    if abs(max_lat-min_lat) > 180 or abs(max_long-min_long) > 180:
        print("samples coords span over 180 degrees lat or long; the code isn't ready to deal with that")
        exit()

    # find a good S— that is, the width of the sampling window
    lat1 = distance.distance([min_lat,min_long], [max_lat,min_long]).km # confirmed ellipsoid='WGS-84' by default
    lat2 = distance.distance([min_lat,max_long], [max_lat,max_long]).km
    long1 = distance.distance([min_lat,min_long], [min_lat,max_long]).km
    long2 = distance.distance([max_lat,min_long], [max_lat,max_long]).km
    S = max([lat1,lat2,long1,long2])

    # set bottom left corner of sampling window
    corner_bl = [min_lat, min_long]

    # bottom right corner: draw line S distance, same lat
    corner_br = list(corner_bl) # starting on top of the bottom left point
    dist_bottom = 0
    while dist_bottom < S:
        corner_br[1] += precision
        dist_bottom = distance.distance(corner_bl, corner_br).km

    # top corners: draw both sides simultaneously
    b=0
    corner_tl = list(distance.distance(kilometers=S).destination(corner_bl, bearing=0))[0:2] # third val is altitude 
    corner_tr = list(distance.distance(kilometers=S).destination(corner_br, bearing=0))[0:2]
    dist_top = distance.distance(corner_tl, corner_tr).km
    if (dist_bottom - dist_top) > 0: # e.g. northern hemisphere
        while dist_top < S:
            b += precision
            corner_tl = list(distance.distance(kilometers=S).destination(corner_bl, bearing=-b))[0:2]
            corner_tr = list(distance.distance(kilometers=S).destination(corner_br, bearing=b))[0:2]
            dist_top = distance.distance(corner_tl, corner_tr).km
    else: # e.g. southern hemisphere
        while dist_top > S:
            b += precision
            corner_tl = list(distance.distance(kilometers=S).destination(corner_bl, bearing=b))[0:2]
            corner_tr = list(distance.distance(kilometers=S).destination(corner_br, bearing=-b))[0:2]
            dist_top = distance.distance(corner_tl, corner_tr).km

    # finally, get individual locs
    from_bottom = abs(coords[:,0] - corner_bl[0])
    from_top = abs(coords[:,0] - corner_tl[0])
    total_y = from_bottom + from_top
    relative_y = (from_bottom / total_y)
    longitudinal_stretch = abs(corner_bl[1]-corner_tl[1])
    from_left = abs(coords[:,1] - (corner_bl[1]-(longitudinal_stretch*relative_y)))
    from_right = abs(coords[:,1] - (corner_br[1]+(longitudinal_stretch*relative_y)))
    total_x = from_left + from_right
    relative_x = (from_left / total_x)
    projection = [relative_x*S, relative_y*S]
    projection = np.array(projection)
    projection = projection.T
    
    return projection


# rescale locs
def rescale_locs(locs):
    locs0 = np.array(locs)
    minx = min(locs0[:, 0])
    maxx = max(locs0[:, 0])
    miny = min(locs0[:, 1])
    maxy = max(locs0[:, 1])
    x_range = maxx - minx
    y_range = maxy - miny
    sample_width = max(x_range, y_range)  # re-define width to be this distance
    locs0[:, 0] = (locs0[:, 0] - minx) / x_range  # rescale to (0,1)
    locs0[:, 1] = (locs0[:, 1] - miny) / y_range
    if x_range > y_range:  # these four lines for preserving aspect ratio
        locs0[:, 1] *= y_range / x_range
    elif y_range > x_range:
        locs0[:, 0] *= x_range / y_range
    locs0 = locs0.T
    sample_width = np.array(sample_width)
    return locs0, sample_width


# pad locations with zeros
def pad_locs(locs, max_n):
    padded = np.zeros((2, max_n))
    n = locs.shape[1]
    padded[:, 0:n] = locs
    return padded


# pre-processing rules:
#     1 biallelic change the alelles to 0 and 1 before inputting.
#     2. no missing data: filter or impute.
#     3. ideally no sex chromosomes, and only look at one sex at a time.
def vcf2genos(vcf_path, max_n, num_snps, phase):
    geno_mat, pos_list = [], []
    vcf = open(vcf_path, "r")
    current_chrom = "XX"
    baseline_pos = 0
    previous_pos = 0
    for line in vcf:
        if line[0] != "#":
            newline = line.strip().split("\t")
            genos = []
            for field in range(9, len(newline)):
                geno = newline[field].split(":")[0].split("/")
                geno = [int(geno[0]), int(geno[1])]
                if phase == 1:
                    genos.append(sum(geno))  # collapsed genotypes
                elif phase == 2:
                    geno = [min(geno), max(geno)]
                    genos.append(geno[0])
                    genos.append(geno[1])
                else:
                    print("problem")
                    exit()
            for i in range((max_n * phase) - len(genos)):  # pad with 0s
                genos.append(0)
            geno_mat.append(genos)

            # deal with genomic position
            chrom = newline[0]
            pos = int(newline[1])
            if chrom == current_chrom:
                previous_pos = int(pos)
            else:
                current_chrom = str(chrom)
                baseline_pos = (
                    int(previous_pos) + 10000
                )  # skipping 10kb between chroms/scaffolds (also skipping 10kb before first snp, currently)
            current_pos = baseline_pos + pos
            pos_list.append(current_pos)

    # check if enough snps
    if len(geno_mat) < num_snps:
        print("not enough snps")
        exit()
    if len(geno_mat[0]) < (max_n * phase):
        print("not enough samples")
        exit()

    # sample snps
    geno_mat = np.array(geno_mat)
    pos_list = np.array(pos_list)
    mask = [True] * num_snps + [False] * (geno_mat.shape[0] - num_snps)
    np.random.shuffle(mask)
    geno_mat = geno_mat[mask, :]
    pos_list = pos_list[mask]

    # rescale positions
    pos_list = pos_list / (max(pos_list) + 1)  # +1 to avoid prop=1.0

    return geno_mat, pos_list


### main
def main():
    vcf_path = sys.argv[1]
    max_n = int(sys.argv[2])
    num_snps = int(sys.argv[3])
    outname = sys.argv[4]
    phase = int(sys.argv[5])
    geno_mat, pos_list = vcf2genos(vcf_path, max_n, num_snps, phase)
    np.save(outname + ".genos", geno_mat)
    np.save(outname + ".pos", pos_list)


if __name__ == "__main__":
    main()
