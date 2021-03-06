#!/usr/bin/env python3
import math as mt
import os
import itertools
import collections
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import scipy.stats
import seaborn as sns
from Bio import SeqIO



class Kmer():

    """This class implements an alignment-free algorithm to correlate genetic sequences.

	The sequence A is cut into "words" of k nucleotides and for all the k reading frames;
    a vector then is filled with the occurrences of each possible words (4**k). The same 
    is made with the sequence B. Finally the two resulting vectors are correlated. If 
    a set of N sequences is given, the class generates N vector that are correlated 
    each other.

    The class includes a method to find bias-corrected and accelerated 
    confidence intervals for the correlation values.

    """

    def __init__(self, seqs=None, length_seqs=None, corrs=None, files=None):
        """It initializes the main attributes of the class.

        Attributes
        ----------
        seqs: 'list'
            A list containing the raw genetic sequences. Letters must be
            upper-case.
        length_seqs: 'list'
            A list containing the length of the genetic sequences in seqs.
            The length is measured in base pairs [bp].
        corr: 'str'
            Correlation function to use among the possible ones:

            - Pearson (P)
            - Spearman (S)
            - Kendall (T)
            - All (ALL)     <---- it correlates the sequences using the 
                                  three functions above. 

            It can be decided a priori. If None, the script will ask for
            one.
            WARNING: the script will either calculate with one correlation
            function or with all of them. The use of two correlations is 
            not possible (e.g. Pearson+Kendall).
        alphabet: 'str'
            The genetic alphabet. Only "ATCG" possible: reduced alphabet not
            supported.
        files: 'list'
            A list containing the sequences' names. If a sequence is
            downloaded from a database, the name usually corresponds to the
            file name.
        k: 'int'
            A parameter defining the length [bp] of an extracted "word".
        all_w: 'list'
            A list containing all the possible permutations given the 
            alphabet and the words' lengths. In this case, 4**k.
        corr_matrix: 'numpy 3-D array'
            A 3-D array that contains the correlation values. It resembles
            an array of matrices: each matrix refers to a correlation
            function.
        ordered_kmers: '2D list'
            A list containing a number of lists equal to the sequences' number.
            Each list contains the occurrences of all the possible words for a
            sequence. The occurrences of each list are sorted by all_w.

        """
        if seqs is None:
            self.seqs = []
            self.length_seqs = []
        else:
            self.seqs = seqs
            self.length_seqs = length_seqs
        self.alphabet = "ATCG"
        if corrs is None:
            self.corr = input("Correlation functions: \n\n-Pearson (P) \
             \n-Spearman (S) \n-Kendall (T) \n-All (ALL) \n\nChoose one of them: ")
        else:
            self.corr = corrs
        if files is None:    
            self.files = []
        self.k = 0
        self.all_w = None
        self.corr_matrix = None
        self.ordered_kmers = None

    def read_seqs(self, rel_path=None):
        """It processes the Genbank (*.gb) and FASTA (*.fasta) files
        to extract the sequences. 

        WARNING: depending on which and how many features one has to
        extract from *.gb files, the code must be changed accordingly.

        """
        if rel_path is None:
            rel_path = input("Insert relative path: ")
        if rel_path[0] == "/" or rel_path[0] == "\\":
            rel_path = rel_path[1:]
        if rel_path[-1] != "/":
            rel_path = rel_path+"/" 
        elif rel_path[-1] != "\\":
            rel_path = rel_path+"\\"
            
        path = os.path.join(os.path.expanduser("~"), rel_path)
        self.files = sorted(os.listdir(path))
        names_taken = []
        for num, fil in enumerate(self.files):
            if fil.endswith(".gb"):
                rec = SeqIO.read(path+fil, "genbank")
                for rec in SeqIO.parse(path+fil, "genbank"):
                    for ff in rec.features:
                        if ff.type == "source":  #this line select the genbank feature
                            seq = ff.location.extract(rec).seq
                            self.length_seqs.append(len(seq))
                            self.seqs.append(seq)
                            names_taken.append(fil)
                            break   #in a *.gb file features can repeat (more studies on same region)
            elif fil.endswith(".fasta"):
                seq = ''.join(SeqIO.read(open(path+fil), "fasta").seq)
                self.length_seqs.append(len(seq))
                if seq[0].islower():   #some fasta file can have lower-case character (by default
                                       #they must be upper-case)
                    seq = seq.upper()
                self.seqs.append(seq)
                names_taken.append(fil)

        self.files = [x for x in self.files if x in names_taken] # to have correspondence between
                                                                 #name and its sequence




    def optimal_k(self, max_k=None):
        """ Given a range of k values, the variety of the extracted
        words in a sequence changes. The method returns the (optimal)
        k(s) for which the variety (or richness) is maximum.
        The methodology is taken from:

        'Alignment-free genome comparison with feature frequency 
        profiles (FFP) and optimal resolutions', (Gregory E. Sims,
        Se-Ran Jun, Guohong A. Wu and Sung-Hou Kima).
        
        """
        min_k = 1
        if max_k is None:
            max_k = 8

        richness = np.zeros((len(self.seqs), max_k - 1))
        opt_k = {}
        k = 0
        for ind, seq in enumerate(self.seqs):
            for k in range(min_k, max_k):
                pos = 0
                end_pos = len(seq) - k + 1
                kmers = []
                for pos in range(0, end_pos):
                    sub = seq[pos:k+pos]
                    if not all(w in self.alphabet for w in sub):
                        continue
                    else:
                        kmers.append(str(sub))
                counting = collections.Counter(kmers)
                for values in counting.values():
                    if values >= 2:
                        richness[ind][k-1] += 1
            opt_k["{}".format(self.files[ind])] = np.argmax(richness[ind]) + 1
        
        print(opt_k)

        return opt_k 




    def words_overlay(self, k=None):
        """The method extracts the words from each sequence given
        the parameter k. If k is None, the function will print
        the average k for the sequences based on the relation:

        k = log_4(sequence length),

        which theoretically finds the best k in the same
        fashion as in optimal_k (check the paper cited in the 
        latter for more informations). Then the user can choose
        the k to use.

        """
        if k is not None:
            self.k = k
        else:
            logs = 0
            average_k = 0
            for n in self.length_seqs:
                logs += mt.log(n, 4)
            average_k = logs / len(self.length_seqs)
            print("Average k: ", average_k)
            self.k = int(input("Choose words' length: "))

        self.all_w = np.empty(4**self.k, dtype=object)
        for index, items in enumerate(itertools.product(self.alphabet, repeat=self.k)):
            self.all_w[index] = ''.join(items)

        print("Extracting words... ")
        #self.count_kmers = [] #[[] for lists in range(len(self.seqs))]
        self.ordered_kmers = [[] for lists in range(len(self.seqs))]
        #if not self.boot_switch:
            #self.sample_size = [[] for lists in range(len(self.seqs))]
        for index, sequence in enumerate(self.seqs):
            pos = 0
            end_pos = len(sequence) - self.k + 1
            kmers = []
            for pos in range(0, end_pos):
                sub = sequence[pos:self.k+pos]
                if not all(w in self.alphabet for w in sub):
                    continue
                else:
                    kmers.append(str(sub))
            unordered_dic_kmers = collections.Counter(kmers)
            for key in self.all_w:
                self.ordered_kmers[index].append(unordered_dic_kmers[key])

        print("Words analysis completed.\n")



    def correlations(self):
        """It correlates N sequences among each other using the words 
        occurrences. Given the symmetric nature of the corr. functions, only 
        N((N-1)/2 + 1) values are calculated.
        
        """        
        self.corr_matrix = [np.zeros((len(self.seqs), len(self.seqs))) for l in range(0, 3)]
        x = 0
        print("Calculating correlations...")
        for x in range(0, len(self.seqs)):
            y = 0
            for y in range(0, len(self.seqs)):
                if x >= y:
                    if self.corr == "S":
                        value = scipy.stats.spearmanr(self.ordered_kmers[x], self.ordered_kmers[y])[0]
                        self.corr_matrix[len(self.corr) - 1][x][y] = value
                    elif self.corr == "T":
                        value = scipy.stats.kendalltau(self.ordered_kmers[x], self.ordered_kmers[y])[0]
                        self.corr_matrix[len(self.corr) - 1][x][y] = value
                    elif self.corr == "P":
                        value = scipy.stats.pearsonr(self.ordered_kmers[x], self.ordered_kmers[y])[0]
                        self.corr_matrix[len(self.corr) - 1][x][y] = value
                    else:
                        spearm = scipy.stats.spearmanr(self.ordered_kmers[x], self.ordered_kmers[y])[0]
                        tau = scipy.stats.kendalltau(self.ordered_kmers[x], self.ordered_kmers[y])[0]
                        pears = scipy.stats.pearsonr(self.ordered_kmers[x], self.ordered_kmers[y])[0]
                        corr = [spearm, tau, pears]
                        for index, corrs in enumerate(corr):
                            self.corr_matrix[index][x][y] = corrs
                else:
                    break

        if self.corr == "ALL":
            stop = len(self.corr_matrix)
        else:
            stop = 1
        for ind in range(0, stop):
            self.corr_matrix[ind] = self.corr_matrix[ind] + self.corr_matrix[ind].T - np.diag(
                self.corr_matrix[ind].diagonal())  #it fills the rest of the array (symmetry)


        print("Done.\n")


    def bootstrapping_BCa(self, alpha=0.04549, tolerance=10, B=10, BCa=True):
        """The method calculates confidence intervals for specific 
        correlation values of a 'model' sequence against N - 1 sequences,
        using bootstrapping and bootstrapping BCa. The parameters must be
        set according to the experiment (type of sequences, statistical 
        significance, computational power, etc.).
        The confidence levels are saved in *.txt format.

        WARNING: the bootstrapping theory makes use of samples generated 
        from the original one. However, between two sequences the corr. 
        value is only one: to have a sample of corr. values, 
        one need a sample of sequences, and the sequences being in 
        such a way that do not differentiate too much from the original ones. 
        This is accomplished sampling with replacement the words 
        (together with the corresponding occurrences) of the original 
        sequences.

        Parameters
        ----------
        alpha: 'float'
        It represents the significance level.
        tolerance: 'int'
        Because of the warning above, it happens that the sequences in
        S do not have the same length of their original ones. The tolerance
        variable forces the system to provide sequences with length L equal
        to L +/- tolerance. Smaller the tolerance, more reliable the 
        bootstrapping, but the computational time rises (exponentially).
        B: 'int'
        Number of bootstraps. Greater the value, stronger the statistics.
        BCa: 'boolean'
        A switch to either perform BCa or not.

        """
        print("Number of bootstraps: ", B)
        print("New sample size`s tolerance: +/- ", tolerance, "occurences")
        CL = 1- alpha
        print("Confidence level: ", CL*100, "%")

        theta_low, theta_up, corr_func = ([[] for l in range(0, 3)] for i in range(3))
        print(theta_low)
        z = scipy. stats.norm.ppf(alpha)
        zop = scipy.stats.norm.ppf(CL)
        x = 0
        if self.corr == "ALL":
            stop = 3 
            #corr_values = [[] for l in range(0,3)]
        else:
            stop = 1      #corr_values = []
            theta_low[1], theta_up[1], corr_func[1] = ([mt.nan]*(len(self.seqs) - 1) for l in range(3))
            theta_low[2], theta_up[2], corr_func[2] = ([mt.nan]*(len(self.seqs) - 1) for l in range(3))
        for x in range(0, 1):
            for y in range(1, len(self.seqs)):
                corr_values = [[] for l in range(0, stop)]
                n = 0
                for n in range(0, B):
                    N = 0
                    M = 0
                    new_size_N = 0
                    new_size_M = 0

                    
                    low_tol_N = sum(self.ordered_kmers[x]) - tolerance
                    up_tol_N = sum(self.ordered_kmers[x]) + tolerance
                    low_tol_M = sum(self.ordered_kmers[y]) - tolerance
                    up_tol_M = sum(self.ordered_kmers[y]) + tolerance
		
                    #the while loop forces the size within the tolerance level
                    while (new_size_N <= low_tol_N  or new_size_N >= up_tol_N) and (
                            new_size_M <= low_tol_M  or new_size_M >= up_tol_M):

                        sample_keys = np.random.choice(self.all_w, len(self.all_w))
                        values_N = []
                        values_M = []

                        for key in sample_keys:
                            index = np.where(self.all_w == key)
                            values_N.append(self.ordered_kmers[x][index[0][0]])
                            values_M.append(self.ordered_kmers[y][index[0][0]])

                        new_size_N = sum(values_N)
                        new_size_M = sum(values_M)

                    if self.corr == "S":
                         corr_values[0].append(scipy.stats.spearmanr(values_N, values_M)[0])
                    elif self.corr == "T":
                        corr_values[0].append(scipy.stats.kendalltau(values_N, values_M)[0])
                    elif self.corr == "P":
                        corr_values[0].append(scipy.stats.pearsonr(values_N, values_M)[0])
                    else:
                        corr_values[0].append(scipy.stats.spearmanr(values_N, values_M)[0])
                        corr_values[1].append(scipy.stats.kendalltau(values_N, values_M)[0])
                        corr_values[2].append(scipy.stats.pearsonr(values_N, values_M)[0])


                corr_values = [sorted(corr_values[h]) for h in range(0, stop)] #len(corr_values))]

                if BCa is True:

                    jack_theta = [[] for l in range(0, stop)]#len(corr_values))]
                    jack_theta_average = [[] for l in range(0, stop)]#len(corr_values))]
                    lower_alpha = []
                    upper_alpha = []
                    k = 0
                    for k in range(0, stop):#len(corr_values)):
                        count = 0
                        j = 0
                        for j in range(0, len(corr_values[k])): #It runs over the elements of a correlation function
                            jack_theta[k].append(sum(l for l in corr_values[k] if l != corr_values[k][j]))
                            if corr_values[k][j] < self.corr_matrix[k][x][y]:
                                count += 1
                                
                        jack_theta[k] = [l / (len(jack_theta[k]) - 1) for l in jack_theta[k]]        
                        jack_theta_average[k].append(sum(jack_theta[k]) / len(jack_theta[k]))
                        accel = (sum(jack_theta_average[k] - l for l in jack_theta[k])**3)/6*((
                            sum(jack_theta_average[k] - l for l in jack_theta[k])**2)**(3/2))
                        z_zero = scipy.stats.norm.ppf(count/B)

                        lower_alpha.append(int(scipy.stats.norm.cdf(z_zero + (z_zero + z)/
                                                                    (1 - accel*(z_zero + z)))*B))
                        upper_alpha.append(scipy.stats.norm.cdf(z_zero + (z_zero + zop)/
                                                                (1 - accel*(z_zero + zop)))*B)
                        if not upper_alpha[k][0].is_integer():
                            upper_alpha[k] = int(upper_alpha[k] + 1)
                        else: upper_alpha[k] = int(upper_alpha[k])

                        theta_low[k].append(corr_values[k][lower_alpha[k] - 1])
                        theta_up[k].append(corr_values[k][upper_alpha[k] - 1])
                        corr_func[k].append(self.corr_matrix[k][x][y])

                else:
                    lower_alpha = int(B*(1 - CL))
                    upper_alpha = CL*B
                    if not upper_alpha.is_integer():
                        upper_alpha = int(upper_alpha + 1)
                    else: 
                        upper_alpha = int(upper_alpha)
                    k = 0    
                    for k in range(0, stop):#len(corr_values)):
                        theta_low[k].append(corr_values[k][lower_alpha - 1])
                        theta_up[k].append(corr_values[k][upper_alpha - 1])
                        corr_func[k].append(self.corr_matrix[k][x][y])

    

        with open("Conf_int.txt", "wb+") as datafile_id:
            data = np.array([theta_low[0], theta_up[0], corr_func[0],
                             theta_low[1], theta_up[1], corr_func[1],
                             theta_low[2], theta_up[2], corr_func[2]])
            data = data.T
            np.savetxt(datafile_id, data, fmt="%f", delimiter="    ", header="SpearCIlow,\
 SpearCIup, Spear, KenCIlow, KenCIup, Ken, PearCIL, PearCIup, Pear")




    def sKmer(self, binning=100):
        """This method cut sequences in subsequences: it is used when
        the user wants to look for local changes in a sequence. The
        method should be called before to perform any words extraction
        as well as correlation calculation. The subsequences get stored
        in the seqs attribute.

        Parameters
        ----------
        binning: 'int'
        It defines the length of the subsequences.
        
        """
        self.binning = binning
        subseqs = []
        for ind, ss in enumerate(self.seqs):
            if ind == 0:
                self.limit = len(ss) // binning
            i = 0
            while i < len(ss) // binning:
                sub = ss[i*binning:(i+1)*binning]
                subseqs.append(sub)
                i += 1
        self.seqs = subseqs




    def histogram(self):
        """It saves/shows the words distribution for a sequence.
        The words extraction must be performed before to call the
        method.

        """
        words = np.arange(4**self.k)
        occurr = self.ordered_kmers

        for ind in range(0, len(occurr)):

            occurr[ind] = [x / sum(occurr[ind]) for x in occurr[ind]]
            plt.clf()
            plt.bar(words, occurr[ind], align="center")
            plt.xticks(words, self.all_w, rotation="vertical")
            plt.title("Set title")
            plt.xlabel("Words")
            plt.ylabel("Frequencies")
            plt.savefig("Namefile{}.png".format(ind), bbox_inches="tight")
            #plt.close()
            #plt.show()



    def heatmap(self, matrix=np.array([])):
        """It visualizes the matrix correlation values via heatmap.
        Each row represents a sequence as well as each column.
        The labels present the sequences' names and, upon request, 
        can be coloured based on the kingdom a sequence belongs. 
        For this, each file name must start with an integer number 
        plus underscore as the following:

        Integer     Kingdom
        -------     -------
        0_          Animalia
        1_          Archaea
        2_          Bacteria
        3_          Fungi
        4_          Plantae
        5_          Protista

        """
        if not matrix.any():
            matrix = self.corr_matrix

        king_switch = input("Do you want labels based on kingdoms? [y/n]: ")
        labels = []
        palettes = []
        colors = ["red", "purple", "blue", "gray", "green", "orange",]
                 #Animalia, Archaea, Bacteria, Fungi, Plantae, Protista

        for files in self.files:
            if king_switch == "y":
                palettes.append(colors[int(files[0])])
                files = files[2:]
            if files.endswith(".gb"):
                namefile = files.replace(".gb", "")
                labels.append(namefile)
            elif files.endswith(".fasta"):
                namefile = files.replace(".fasta", "")
                labels.append(namefile)


        x = 0
        if self.corr == "ALL":
            stop = len(self.corr_matrix)
            name_corr = ["Spearman", "Kendall", "Pearson"]
        else:
            stop = 1

        for ind in range(0, stop):
            plt.clf()
            plt.figure()
            points = sns.heatmap(self.corr_matrix[ind], square=True, vmin=-1, vmax=1,
                                 xticklabels=labels, yticklabels=labels, cmap="RdBu_r", linewidths=.1,
                                 cbar_kws={"ticks":[-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1]}, fmt=".2f",
                                 annot=False, annot_kws={"size": 9})
            plt.xticks(rotation=90)
            plt.yticks(rotation=0)
            red_patch = mpatches.Patch(color="red", label="Animalia")
            purple_patch = mpatches.Patch(color="purple", label="Archaea")
            blue_patch = mpatches.Patch(color="blue", label="Bacteria")
            gray_patch = mpatches.Patch(color="gray", label="Fungi")
            green_patch = mpatches.Patch(color="green", label="Plantae")
            orange_patch = mpatches.Patch(color="orange", label="Protista")
            #plt.legend(handles = [red_patch, purple_patch, blue_patch], loc = 3, bbox_to_anchor = (-0.4, -0.3))
            plt.tight_layout()
            #plt.yticks(range(len(self.files)), labels)
            if king_switch == "y":
                for ind, label in enumerate(points.get_yticklabels()):
                    label.set_color(palettes[::-1][ind])
                for ind, label in enumerate(points.get_xticklabels()):
                    label.set_color(palettes[ind])
            plt.title("Set title")
            plt.savefig("Namefile{}.png".format(ind), bbox_inches="tight")



    def heatmap_sKmer(self):
        """ It visualizes the matrix correlation values via heatmap when
        sKmer is applied. Each row represents the subsequences of a sequence Y
        while each column represents the subsequences of a sequence X.

        """
        if self.corr == "ALL":
            stop = len(self.corr_matrix)
            name_corr = ["Spearman", "Kendall", "Pearson"]
        else:
            stop = 1
            name_corr = [self.corr]
        for ind in range(0, stop):
            plt.clf()
            fig = plt.figure()
            ax = fig.add_subplot(111)
            points = sns.heatmap(self.corr_matrix[ind][0:self.limit, self.limit:],
                                 square=True, vmin=-1, vmax=1, cmap="RdBu_r", linewidths=.1,
                                 cbar_kws={"ticks":[-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1]},
                                 fmt=".2f", annot=False, xticklabels=10, yticklabels=10,
                                 annot_kws={"size": 9})
            ax.plot([0, ax.get_ylim()[1]], [ax.get_ylim()[1], 0], ls="--", color=".3",
                    linewidth=1.)

            plt.title("sKmer - {} corr. for k = {} and bin = {} bp".format(
                      name_corr[ind], self.k, self.binning))
            plt.xlabel("Subsequences X [(x+1)*{} bp]".format(self.binning))
            plt.ylabel("Subsequences Y [(y+1)*{} bp]".format(self.binning))
            plt.savefig("Namefile{}.png".format(ind), bbox_inches="tight")
            #plt.pause(0.001)
            #plt.close()



if __name__ == "__main__":

    quest = Kmer()
    quest.read_seqs(rel_path="/relative/path/to/files")
    decision = input("Do you want to perform sKmer? [y/n] ")
    if decision == "y":
        quest.sKmer()
    quest.words_overlay()
    quest.correlations()
    if decision == "y":
        quest.heatmap_sKmer()
    else:
    	quest.heatmap()    
    #quest.bootstrapping_BCa()
    
                
