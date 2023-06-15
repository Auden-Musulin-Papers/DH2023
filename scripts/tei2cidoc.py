import os
from tqdm import tqdm
from acdh_cidoc_pyutils.namespaces import CIDOC
from acdh_tei_pyutils.tei import TeiReader
from rdflib import Graph, Namespace, URIRef, Literal, plugin, ConjunctiveGraph
from rdflib.namespace import RDF, RDFS
from rdflib.store import Store

# set up the graph
domain = "https://amp.acdh.oeaw.ac.at/"
AMP = Namespace(domain)

store = plugin.get("Memory", Store)()
uri = URIRef(domain)
g = Graph(store=store, identifier=uri)
g.bind("amp", AMP)
g.bind("crm", CIDOC)

# create output directory
rdf_dir = "./rdf"
os.makedirs(rdf_dir, exist_ok=True)

# parse TEI/XML
doc = TeiReader("./data/dh2023-xml-amp-transcript__0004.xml")
nsmap = doc.nsmap
items = doc.any_xpath(".//tei:event")
# create event types
assertive = URIRef(f"{AMP}event/types/assertive")
non_assertive = URIRef(f"{AMP}event/types/non-assertive")
nano_publication = URIRef(f"{AMP}event/types/nano-publication")
g.add((assertive, RDF.type, CIDOC["E55_Type"]))
g.add((non_assertive, RDF.type, CIDOC["E55_Type"]))
g.add((nano_publication, RDF.type, CIDOC["E55_Type"]))
# create event based on TEI
for x in tqdm(items, total=len(items)):
    xml_id = x.attrib["{http://www.w3.org/XML/1998/namespace}id"]
    item_id = f"{AMP}{xml_id}"
    subj = URIRef(item_id)
    event_type = x.attrib["type"]
    if event_type == "assertive":
        g.add((subj, RDF.type, assertive))
        date_from = x.attrib["notBefore"]
        date_to = x.attrib["notAfter"]
        g.add((subj, CIDOC["P82a_begin_of_the_begin"], Literal(date_from)))
        g.add((subj, CIDOC["P82b_end_of_the_end"], Literal(date_to)))
        corresp = x.attrib["corresp"]
        g.add((subj, CIDOC["P123_resulted_in"], URIRef(f"{AMP}{corresp.split('#')[-1]}")))
    elif event_type == "non-assertive":
        g.add((subj, RDF.type, non_assertive))
        # create sub-event properties
        resp = x.attrib["resp"]
        cert = x.attrib["cert"]
        date_from = x.attrib["from"]
        date_to = x.attrib["to"]
        g.add((subj, CIDOC["E91_co_reference_assignment"], Literal(cert)))
        g.add((subj, CIDOC["P1_is_identified_by"], Literal(resp)))
        g.add((subj, CIDOC["P82a_begin_of_the_begin"], Literal(date_from)))
        g.add((subj, CIDOC["P82b_end_of_the_end"], Literal(date_to)))
        source = x.attrib["source"]
        source_uri = URIRef(f"{AMP}{source.split('https://doi.org/')[-1]}")
        g.add((source_uri, RDF.type, nano_publication))
        g.add((source_uri, CIDOC["P70_is_documented_in"], URIRef(source)))
        g.add((source_uri, CIDOC["P123_resulted_from"], subj))
        g.add((subj, CIDOC["P123_resulted_in"], source_uri))
        corresp = x.attrib["corresp"]
        g.add((subj, CIDOC["P123_resulted_from"], URIRef(f"{AMP}{corresp.split('#')[-1]}")))
    else:
        print("event is not assertive or non-assertive")
    g.add((subj, RDF.type, CIDOC["E5_Event"]))
    label = " ".join(x.xpath("./tei:label//text()", namespaces=doc.nsmap))
    g.add((subj, RDFS.label, Literal(label)))
    desc = " ".join(x.xpath("./tei:desc//text()", namespaces=doc.nsmap))
    g.add((subj, RDFS.comment, Literal(desc)))
g_all = ConjunctiveGraph(store=store)
g_all.serialize(destination=os.path.join(rdf_dir, "events.ttl"), format="turtle")
g_all.serialize(destination=os.path.join(rdf_dir, "events.trig"), format="trig")
