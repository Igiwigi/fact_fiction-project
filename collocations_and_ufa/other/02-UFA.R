# A R script for performing Usage Fluctuation Analysis on collocates over time

# This script is included in the supplementary material in order to show
#the main logic of the code.

# The supplementary material does not include copies of our text corpus,
# so this code will not currently produce any outputs.

# This code was freely adapted from the R code made available on the UFA tool
# available from the Lancaser University corpus linguistic toolbox: 
# http://corpora.lancs.ac.uk/stats/toolbox.php 

rm(list=ls())
# Import libraries
library(fs)
library(tidyverse)
library(reshape2)
library(irrCAC)

setwd("~/UFA-project/")
# Read from dir
data_dir <- "results/work/"
antconc_input <- fs::dir_ls(data_dir, regexp = "\\.csv$")
#  skip comments; filename, MI>=3, collocate; transpose; collocate as index
data <- antconc_input %>% 
  map_dfr(readr::read_tsv, col_names = TRUE, col_types = "dcdd", comment="#", .id="source") %>%
  select(source,word,collocations) %>%
  spread(key = source, value = collocations, fill=0)

# Collocation matrix - 1 = collocate present; 0 = not present
coll <- data %>% 
  mutate_if(is.numeric, ~1 * (. != 0))

# Write to table for extracting collocate types
write.table(coll , file = "colls/inheritance.csv", sep="\t")

# counter
i = 0
# empty vector
v <- c()
# Calculate Gwet's AC1; append to vector
while(i+1 < ncol(coll)) {
  n = (gwet.ac1.raw(coll[,i:(i+2)])$est$coeff.val)
  v <- c(v, n)
  i = i+1
}

# Prepare date span
# NB! These variables need to be changed, depending on the slice of data
from = 1837
to = 1905
# Create DataFrame
h <- seq(from, to, by = 1)
g <- data.frame(h, v)

# Produce graph
# NB! by needs to be changed for larger windows
p <- ggplot(g, aes(x = g[,1], y =g[,2])) + 
  scale_x_continuous(breaks = seq(1837, to, by = 10)) + 
  ylim(0.7,1.05) +
  geom_point() + 
  xlab("Time") + 
  ylab("AC1") 

# Additive model
# NB! K needs to be changed for larger windows
p + stat_smooth(method = "gam", 
                formula = y ~ s(x, bs = "cr", fx=FALSE, k = 10), 
                size = 1, fill="#707070", level = 0.95) + 
  stat_smooth(method = "gam", 
              formula = y ~ s(x, bs = "cr", fx=FALSE, k = 10), 
              size = 1, fill="#FFFF00",level = 0.995)

# change filename
ggsave(
  "output/1837-1914.work.png",
  plot = last_plot(),
  units = c("in", "cm", "mm"),
  dpi = 300,
)
