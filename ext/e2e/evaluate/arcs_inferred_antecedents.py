"""
Usage: python arcs_inferred_antecedents.py key_file.conll response_file.conll
"""

import re,sys,pdb

"""settings"""
def evaluate(gold_path, predicted_path):
    #noun_pos_tags=['NN','NE']                                               #German tag set
    #pronoun_pos_tags=['PPER','PPOSAT','PRELS']                              #German tag set
    noun_pos_tags=['NN','NNS','NNP','NNPS']                                 #English tag set
    pronoun_pos_tags=['PRP','PRP$']                                         #English
    pos_index=4                                                             #list index of the POS tag in the split key/response file
    lexem_index=3                                                           #list index of the lexem/lemma in the split key/response file
    
    all_key=re.split('#end document[^\n]*',open(gold_path,'r').read())    #split documents at lines starting with "#end document", consume everything except newline
    all_res=re.split('#end document[^\n]*',open(predicted_path,'r').read())
    if re.match('\n+',all_key[-1]): del all_key[-1]                         #delete splitting artefacts
    if re.match('\n+',all_res[-1]): del all_res[-1]
    
    if len(all_key)!=len(all_res): 
        print('Key and response file do not have the same number of documents. The key file has',len(all_key),'documents, the response file has',len(all_res))
        pdb.set_trace()
    
    non_nominal_sets=0                                                      #counter for sets without nominal mentions
    sets=0                                                                  #coreference set counter
    cataphora=0                                                             #counter for sets starting with a non-nominal mention, i.e. most likely a pronoun
    
    evaluation={}                                                           #global evaluation dictionary
    evaluation_prp={}                                                       #global pronoun evaluation dictionary
    
    tp=fp=wl=fn=0                                                           #global true positive, wrong linkage, and negative counts
    
    doc_ids=[]                                                              #document names
    docs={'key':{},'res':{}}
    
    
    """ gather coreference annotation from the key and response files """
    
    #load the documents from the key
    for doc in all_key:
        if not doc.lstrip().startswith('#begin'):
            print("No '#begin document...' at key document beginning")       #every doc should start with this
            pdb.set_trace()
        else:
            key=re.sub('\n{3,}','\n\n',doc)                                 #normalize multiple newlines
            key=key.lstrip().split('\n')                                    #lstrip to remove newlines at document beginning    
            docid=re.search('#begin document ([^\n]+)',key[0]).group(1)     #document id
            docs['key'][docid]=key
            doc_ids.append(docid)
    
    #load the documents from the response
    for doc in all_res:
        if not doc.lstrip().startswith('#begin'):
            print("No '#begin document...' at response document beginning")
            pdb.set_trace()
        else:
            res=re.sub('\n{3,}','\n\n',doc)
            res=res.lstrip().split('\n')
            docid=re.search('#begin document ([^\n]+)',res[0]).group(1)
            docs['res'][docid]=res
            if not docid in doc_ids: doc_ids.append(docid)
    
    #process each document        
    for doc in doc_ids:                                                     #for each document name in the key
        if not doc in docs['key']:
            print(doc,'is in the response, but not in the key. Enter c to continue ommiting the document or q to quit...')
            pdb.set_trace()
            continue                                                        #ommit documents not in key/res
        
        if not doc in docs['res']: 
            print(doc,'is in the key but not in the response. Enter c to continue ommiting the document or q to quit...')
            pdb.set_trace()
            continue                                                        #ommit documents not in key/res
            
        key=docs['key'][doc]
        res=docs['res'][doc]
        if len(key)!=len(res): 
            print('Key and response document have not the same number of lines. Key has',len(key),'lines. The response has',len(res),'lines.')
            pdb.set_trace()
        
        #gather key coreference sets
        key_sets={}
        for line in key:                                                    #process key file line by line
            if line.startswith('#'):                                        #new document
                print(line)
                sent_nr=0                                                   #reset sentence/token counters
                token_nr=1                
            elif line=='': 
                sent_nr+=1                                                  #newline, i.e. new sentence
                token_nr=1            
            elif not line.endswith('-') and not line.endswith('_'):         #we have coreference information
                line=re.split(' +|\t',line)                                 #allow both mutliple spaces and tab separation for robustness
                ids=line[-1].split('|')                                     #split coref annotation             
                for id in ids:                
                    if id.startswith('(') and id.endswith(')'):             #single word term
                        id=re.search('\d+',id).group()                      #numeric coref id
                        #store sentence number, mention token start and end id, PoS tag and lexem 
                        #PoS tag and lexem only for SWTs, MWTs are considered nouns and their lexem is not stored
                        if id in key_sets: key_sets[id].append([sent_nr,token_nr,token_nr,line[pos_index],line[lexem_index]])
                        else: key_sets[id]=[[sent_nr,token_nr,token_nr,line[pos_index],line[lexem_index]]]              
                    elif id.startswith('('):                                #start of multiple word term
                        id=re.search('\d+',id).group()                      #add an incomplete mention, i.e. only sentence number and token start id
                        if id in key_sets: key_sets[id].append([sent_nr,token_nr])
                        else: key_sets[id]=[[sent_nr,token_nr]]              
                    elif id.endswith(')'):                                  #end of multi word term
                        id=re.search('\d+',id).group()
                        for m in key_sets[id]:                              #find the open mention in the chain
                            if len(m)==2: 
                                m.append(token_nr)                          #and append token end id
                                break                        
                token_nr+=1            
            else: token_nr+=1
    
        #gather response coreference sets
        res_sets={}
        for line in res:            
            if line.startswith('#'): 
                sent_nr=0
                token_nr=1                
            elif line=='': 
                sent_nr+=1
                token_nr=1
            elif not line.endswith('-') and not line.endswith('_'):
                line=re.split(' +|\t',line)
                ids=line[-1].split('|')
                for id in ids:                                    
                    if id.startswith('(') and id.endswith(')'):
                        id=re.search('\d+',id).group()
                        if id in res_sets: res_sets[id].append([sent_nr,token_nr,token_nr,line[pos_index],line[lexem_index]])
                        else: res_sets[id]=[[sent_nr,token_nr,token_nr,line[pos_index],line[lexem_index]]]              
                    elif id.startswith('('):
                        id=re.search('\d+',id).group()
                        if id in res_sets: res_sets[id].append([sent_nr,token_nr])
                        else: res_sets[id]=[[sent_nr,token_nr]]              
                    elif id.endswith(')'):
                        id=re.search('\d+',id).group()
                        if not id in  res_sets:
                            print('coref id of closing mention not found in the response')
                            print(line)
                            print(res_sets)
                            pdb.set_trace()
                        for m in res_sets[id]:
                            if len(m)==2: 
                                m.append(token_nr)
                                break                   
                token_nr+=1            
            else: token_nr+=1            
        
        key_sets=sorted(key_sets.values())                                  #turn key and response into sorted list of lists
        res_sets=sorted(res_sets.values())
        
        #start comparing key and response sets on mention basis    
        doc_tp=doc_fp=doc_wl=doc_fn=0                                       #set up counters for the document at hand
        evaluation_doc={}
        
        #Recall: we compare key to response mentions   
        for cset in key_sets:                                               #for every chain in the key
        
            if len(cset)==1: continue                                       #singleton, ommit
            sets+=1                                                         #count the number of sets
            
            if [m for m in cset if len(m)==3 or m[3] in noun_pos_tags]==[]: #check if the set has a nominal mention
                non_nominal_sets+=1
                continue                                                    #only evaluate chains containing nominals
                
            for key_m in cset[1:]:                                          #for every mention in the chain except the first one
                
                #determine POS tag of the mention
                if len(key_m)==5 and not key_m[3] in noun_pos_tags: pos=key_m[3]   #single word term has length 5, mwt length 3
                else: pos='NOUN'
    
                if [m for m in cset[:cset.index(key_m)] if len(m)==3 or m[3] in noun_pos_tags]==[] and pos in pronoun_pos_tags:       #no nominal ante for key_m -> cataphora
                    cataphora+=1
                    continue
    
                #update evaluation dictionaries
                if not pos in evaluation: evaluation[pos]={'tp':0,'wl':0,'fn':0,'fp':0,'true mentions':0}           #global
                evaluation[pos]['true mentions']+=1
                if not pos in evaluation_doc: evaluation_doc[pos]={'tp':0,'wl':0,'fn':0,'fp':0,'true mentions':0}   #document
                evaluation_doc[pos]['true mentions']+=1
                if pos in pronoun_pos_tags:                                 #pronouns
                    if not pos in evaluation_prp: evaluation_prp[pos]={}
                    if not key_m[-1].lower() in evaluation_prp[pos]: evaluation_prp[pos][key_m[-1].lower()]={'tp':0,'wl':0,'fn':0,'fp':0,'true mentions':0}
                    if not cset.index(key_m)==0: evaluation_prp[pos][key_m[-1].lower()]['true mentions']+=1         #pronoun lexem, lowercased
                
                #find the response set(s) containing the key mention
                res_set=[c for c in res_sets if key_m in c]
    
                #start evaluation            
                if res_set==[]:                                             #key mention is not in the reponse -> false negative
                    fn+=1
                    doc_fn+=1
                    evaluation[pos]['fn']+=1
                    evaluation_doc[pos]['fn']+=1
                    if pos in pronoun_pos_tags: evaluation_prp[pos][key_m[-1].lower()]['fn']+=1
                elif len(res_set)>1:                                        #key mention is in multiple response sets -> abort evaluation
                    print('Mention in multiple chains. Mention:',key_m)
                    print('Response chains:')
                    for c in res_set: print(c)
                    pdb.set_trace()
                else:
                    #the mention is the chain starter in the response, but not in the key 
                    #-> recall error, it is anaphoric in the key, but not in the response -> false negative
                    if res_set[0].index(key_m)==0:
                        fn+=1
                        doc_fn+=1
                        evaluation[pos]['fn']+=1
                        evaluation_doc[pos]['fn']+=1
                        if pos in pronoun_pos_tags: evaluation_prp[pos][key_m[-1].lower()]['fn']+=1
                        
                    else:                                                   #we have exactly one response chain containing the mention
                        #find the closest preceding nominal antecedent             
                        nominal_antes=[m for m in res_set[0][:res_set[0].index(key_m)] if len(m)==3 or m[3] in noun_pos_tags]
                        if nominal_antes==[]:                               #no nominal antecedent in the reponse chain -> false negatives, as entity can't be inferred
                            try: 
                                next(m for m in cset[:cset.index(key_m)] if len(m)==3 or m[3] in noun_pos_tags)   #key has a nominal antecedent
                                fn+=1
                                doc_fn+=1
                                evaluation[pos]['fn']+=1
                                evaluation_doc[pos]['fn']+=1
                                if pos in pronoun_pos_tags: evaluation_prp[pos][key_m[-1].lower()]['fn']+=1
                            except StopIteration: continue                  #no nominal antecedent in the key, either, skip
                                
                        else:                                               #we have nominal antecedents in the response chain
                            if nominal_antes[-1] in cset:                   #the closest nominal antecedent in the reponse chain is an antecedent in the key chain
                                tp+=1
                                doc_tp+=1
                                evaluation[pos]['tp']+=1
                                evaluation_doc[pos]['tp']+=1
                                if pos in pronoun_pos_tags: evaluation_prp[pos][key_m[-1].lower()]['tp']+=1                    
                            else:                                           #the closest nominal antecedent is not correct, i.e. not in the key chain
                                wl+=1
                                doc_wl+=1
                                evaluation[pos]['wl']+=1
                                evaluation_doc[pos]['wl']+=1
                                if pos in pronoun_pos_tags: evaluation_prp[pos][key_m[-1].lower()]['wl']+=1
                          
        #Precision: find spurious mentions, i.e. response mentions that are not in the key
        for cset in res_sets:                                               #for all chains in the reponse
            if len(cset)==1  or [m for m in cset if len(m)==3 or m[3] in noun_pos_tags]==[]: continue   #singleton, or no nominal mentions -> ommit
            for res_m in cset[1:]:
                if len(res_m)==5 and not res_m[3] in noun_pos_tags: pos=res_m[3]   #determine POS
                else: pos='NOUN'            
                if not pos in evaluation: evaluation[pos]={'tp':0,'wl':0,'fn':0,'fp':0,'true mentions':0}
                if not pos in evaluation_doc: evaluation_doc[pos]={'tp':0,'wl':0,'fn':0,'fp':0,'true mentions':0}         
                if pos in pronoun_pos_tags: 
                    if not pos in evaluation_prp: evaluation_prp[pos]={}
                    if not res_m[-1].lower() in evaluation_prp[pos]: evaluation_prp[pos][res_m[-1].lower()]={'tp':0,'wl':0,'fn':0,'fp':0,'true mentions':0}            
                    
                key_set=[c for c in key_sets if res_m in c]                 #is the mention in a key chain?
    
                #no nouns in either key or response chain, ommit
                if key_set!=[] and [m for m in key_set[0][:key_set[0].index(res_m)] if len(m)==3 or m[3] in noun_pos_tags]==[] and [m for m in cset[:cset.index(res_m)] if len(m)==3 or m[3] in noun_pos_tags]==[]: continue
                            
                #The response set has a nominal antecedent, but the key set doesn't -> fp, as nominal antecedent is inferred
                elif key_set!=[] and [m for m in key_set[0][:key_set[0].index(res_m)] if len(m)==3 or m[3] in noun_pos_tags]==[] and [m for m in cset[:cset.index(res_m)] if len(m)==3 or m[3] in noun_pos_tags]!=[]:
                    fp+=1
                    doc_fp+=1
                    evaluation[pos]['fp']+=1
                    evaluation_doc[pos]['fp']+=1
                    if pos in pronoun_pos_tags: evaluation_prp[pos][res_m[-1].lower()]['fp']+=1       
                
                #the mention is not in any key chain, or the mention is anaphoric in the response but not in the key
                elif key_set==[] or key_set[0].index(res_m)==0:               
                    fp+=1
                    doc_fp+=1
                    evaluation[pos]['fp']+=1
                    evaluation_doc[pos]['fp']+=1 
                    if pos in pronoun_pos_tags: evaluation_prp[pos][res_m[-1].lower()]['fp']+=1
                          
               
        #Document evaluation                    
        #Recall
        if doc_tp+doc_wl+doc_fn==0: 
            if doc_tp+doc_fn==0: recall=0.0                                  #no coref annotation
            else: pdb.set_trace()
        else: recall=float(doc_tp)/(doc_tp+doc_wl+doc_fn)
        #Precision    
        if doc_tp+doc_wl+doc_fp==0:
            if doc_tp+doc_fp==0: precision=0.0                               #no coref annotation, no incorrectly resolved markables
            else: pdb.set_trace()
        else: precision=float(doc_tp)/(doc_tp+doc_wl+doc_fp)
        #Accuracy
        if doc_tp+doc_wl==0: acc=0.0
        else: acc=float(doc_tp)/(doc_tp+doc_wl)
        #F1
        if precision+recall==0: f1=0
        else:f1=(2 * ((precision*recall)/(precision+recall)))
        
        true_mentions=sum([evaluation_doc[pos]['true mentions'] for pos in evaluation_doc.keys()])  #true mention count
        
        print('Overall\t',)
        print('R:', "%.2f" % (recall*100),'%\t',)
        print('P:', "%.2f" % (precision*100),'%\t',)
        print('F1:', "%.2f" % (f1*100),'%\t',)
        print('Acc:',"%.2f" % (acc*100),'%\t','(tp:',doc_tp,'| wl:',doc_wl,'| fn:',doc_fn,'| fp:',doc_fp,'| true mentions:',str(true_mentions)+')')
        print('-----------------------------------------------------------------------------------------------------------------------------')
        for pos_tag in evaluation_doc:
            print(pos_tag,'\t',)
            doc_tp=evaluation_doc[pos_tag]['tp']
            doc_wl=evaluation_doc[pos_tag]['wl']
            doc_fn=evaluation_doc[pos_tag]['fn']
            doc_fp=evaluation_doc[pos_tag]['fp']
            true_mentions=evaluation_doc[pos_tag]['true mentions']
            #Recall
            if doc_tp+doc_wl+doc_fn==0: 
                if doc_tp+doc_fn==0: recall=0.0
                else: pdb.set_trace()
            else: recall=float(doc_tp)/(doc_tp+doc_wl+doc_fn)
            #Precision    
            if doc_tp+doc_wl+doc_fp==0:
                if doc_tp+doc_fp==0: precision=0.0
                else:pdb.set_trace()
            else: precision=float(doc_tp)/(doc_tp+doc_wl+doc_fp)
            #Accuracy
            if doc_tp+doc_wl==0: acc=0.0
            else: acc=float(doc_tp)/(doc_tp+doc_wl)
            #F1
            if precision+recall==0: f1=0.0
            else:f1=(2 * ((precision*recall)/(precision+recall)))
            
            print('R:', "%.2f" % (recall*100),'%\t',)
            print('P:', "%.2f" % (precision*100),'%\t',)
            print('F1:', "%.2f" % (f1*100),'%\t',)
            print('Acc:',"%.2f" % (acc*100),'%\t','(tp:',doc_tp,'| wl:',doc_wl,'| fn:',doc_fn,'| fp:',doc_fp,'| true mentions:',str(true_mentions)+')')
        print('')
    
    
    #Evaluation of all documents
    print('TOTAL')        
    #Recall
    if tp+wl+fn==0: 
        if tp+fn==0: recall=0.0                                  #no coref annotation
        else: pdb.set_trace()
    else: recall=float(tp)/(tp+wl+fn)
    #Precision    
    if tp+wl+fp==0:
        if tp+fp==0: precision=0.0                               #no coref annotation, no incorrectly resolved marable
        else:pdb.set_trace()
    else: precision=float(tp)/(tp+wl+fp)
    #Accuracy
    if tp+wl==0: acc=0.0
    else: acc=float(tp)/(tp+wl)
    #F1
    if precision+recall==0: f1=0
    else:f1=(2 * ((precision*recall)/(precision+recall)))
    
    true_mentions=sum([evaluation[pos]['true mentions'] for pos in evaluation.keys()])
    
    #sort pos tags by frequency
    sorted_pos=sorted([(evaluation[pos]['true mentions'],pos) for pos in evaluation.keys()],reverse=True)
    sorted_pos=[pos[1] for pos in sorted_pos]
    
    print('Overall\t',)
    print('R:', "%.2f" % (recall*100),'%\t',)
    print('P:', "%.2f" % (precision*100),'%\t',)
    print('F1:', "%.2f" % (f1*100),'%\t',)
    print('Acc:',"%.2f" % (acc*100),'%\t','(tp:',tp,'| wl:',wl,'| fn:',fn,'| fp:',fp,'| true mentions:',str(true_mentions)+')')
    print('-----------------------------------------------------------------------------------------------------------------------------')
    final_r = recall
    final_p = precision
    final_f1 = f1
    for pos_tag in sorted_pos:
        print(pos_tag,'\t',)
        tp=evaluation[pos_tag]['tp']
        wl=evaluation[pos_tag]['wl']
        fn=evaluation[pos_tag]['fn']
        fp=evaluation[pos_tag]['fp']
        true_mentions=evaluation[pos_tag]['true mentions']
        #Recall
        if tp+wl+fn==0: 
            if tp+fn==0: recall=0.0                                  #no coref annotation
            else: pdb.set_trace()
        else: recall=float(tp)/(tp+wl+fn)
        #Precision    
        if tp+wl+fp==0:
            if tp+fp==0: precision=0.0                               #no coref annotation, no incorrectly resolved markables
            else:pdb.set_trace()
        else: precision=float(tp)/(tp+wl+fp)
        #Accuracy
        if tp+wl==0: acc=0.0
        else: acc=float(tp)/(tp+wl)
        #F1
        if precision+recall==0: f1=0
        else:f1=(2 * ((precision*recall)/(precision+recall)))
        
        print('R:', "%.2f" % (recall*100),'%\t',)
        print('P:', "%.2f" % (precision*100),'%\t',)
        print('F1:', "%.2f" % (f1*100),'%\t',)
        print('Acc:',"%.2f" % (acc*100),'%\t','(tp:',tp,'| wl:',wl,'| fn:',fn,'| fp:',fp,'| true mentions:',str(true_mentions)+')')
    print('')
    
    print('Pronouns detailed')
    print('-----------------------------------------------------------------------------------------------------------------------------')
    
    for pos in evaluation_prp:
        print(pos)
        sorted_lexem=sorted([(evaluation_prp[pos][lexem]['true mentions'],lexem) for lexem in evaluation_prp[pos]],reverse=True)
        sorted_lexem=[lexem[1] for lexem in sorted_lexem]
        for lexem in sorted_lexem:
            print(lexem,'\t',)
            tp=evaluation_prp[pos][lexem]['tp']
            wl=evaluation_prp[pos][lexem]['wl']
            fn=evaluation_prp[pos][lexem]['fn']
            fp=evaluation_prp[pos][lexem]['fp']
            true_mentions=evaluation_prp[pos][lexem]['true mentions']
            #Recall
            if tp+wl+fn==0: 
                if tp+fn==0: recall=0.0                                  #no coref annotation
                else: pdb.set_trace()
            else: recall=float(tp)/(tp+wl+fn)
            #Precision    
            if tp+wl+fp==0:
                if tp+fp==0: precision=0.0                               #no coref annotation, no incorrectly resolved markables
                else:pdb.set_trace()
            else: precision=float(tp)/(tp+wl+fp)
            #Accuracy
            if tp+wl==0: acc=0.0
            else: acc=float(tp)/(tp+wl)
            #F1
            if precision+recall==0: f1=0
            else:f1=(2 * ((precision*recall)/(precision+recall)))
            
            print('R:', "%.2f" % (recall*100),'%\t',)
            print('P:', "%.2f" % (precision*100),'%\t',)
            print('F1:', "%.2f" % (f1*100),'%\t',)
            print('Acc:',"%.2f" % (acc*100),'%\t','(tp:',tp,'| wl:',wl,'| fn:',fn,'| fp:',fp,'| true mentions:',str(true_mentions)+')')
        print('')
    
    print('total chains:',sets)
    print('key chains without nouns:',non_nominal_sets)
    print('chains starting with cataphora:',cataphora)
    return final_r, final_p, final_f1