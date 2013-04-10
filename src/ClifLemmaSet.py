'''
Created on 2013-03-31

@author: Torsten Hahmann
'''

import sys
from src import *
import filemgt, process, clif, commands, ladr
from src.ReasonerSet import * 
import os, datetime, logging

class LemmaModule(ClifModule):

    '''
    classdocs
    '''
    def __init__(self, module_name, ladr_file_name, tptp_sentence):
        '''
        Constructor
        '''
        #super(LemmaModule, self).preprocess_clif_file()
        self.depth = 0
        self.parents = []
        self.module_name = module_name
        self.p9_file_name = ladr_file_name
        # THIS IS UNIQUE to the LemmaModule
        self.tptp_sentence = tptp_sentence

        logging.getLogger(self.__module__ + "." + self.__class__.__name__).debug('constructing lemma module: ' + self.module_name)


class ClifLemmaSet(object):
    
    def __init__ (self, name):
        self.p9_file_name = ''
        self.tptp_file_name = ''
        
        self.module = ClifModule(name,0)
        logging.getLogger(__name__).debug('constructed clif module for lemma file: ' + self.module.module_name)
        
        self.module.get_p9_file_name()
        
        self.lemmas = []
        self.add_lemmas()

    
    def get_number_of_lemmas (self):
        return len(lemmas)


    def add_lemmas (self):
        
        # first get LADR translation of ClifModule
        # logging.getLogger(__name__).debug("CREATING LADR TRANSLATION OF LEMMA: " + self.module.module_name)
        #self.module.get_p9_file_name()
        
        (lemma_names, ladr_files) = ladr.get_ladr_goal_files(self.module.get_p9_file_name(), self.module.module_name)
        logging.getLogger(__name__).debug("CREATED LADR TRANSLATION OF LEMMA: " + self.module.get_p9_file_name())

        # translate to tptp as goal
        tptp_sentences = clif.to_tptp([self.module.clif_processed_file_name], axiom=False)
        
        for t in tptp_sentences:
            print t

        # populate the list of lemmas        
        for i in range(0,len(ladr_files)):
            name = os.path.join(os.path.dirname(lemma_names[i]),
                                os.path.basename(ladr_files[i].replace(filemgt.read_config('ladr','ending'),'')))
            print "NAME = " + name
            m = LemmaModule(name,ladr_files[i],tptp_sentences[i])
            self.lemmas.append(m)
        
    def get_lemmas (self):
        return self.lemmas
