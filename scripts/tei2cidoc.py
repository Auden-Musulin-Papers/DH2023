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
nano_publication = URIRef(f"{AMP}event/nano-publication")
g.add((assertive, RDF.type, CIDOC["P2_has_type"]))
g.add((non_assertive, RDF.type, CIDOC["P2_has_type"]))
g.add((nano_publication, RDF.type, CIDOC["P2_has_type"]))
# create event based on TEI
for x in tqdm(items, total=len(items)):
    xml_id = x.attrib["{http://www.w3.org/XML/1998/namespace}id"]
    item_id = f"{AMP}{xml_id}"
    subj = URIRef(item_id)
    event_type = x.attrib["type"]
    if event_type == "assertive":
        g.add((subj, RDF.type, assertive))
    elif event_type == "non-assertive":
        g.add((subj, RDF.type, non_assertive))
    else:
        g.add((subj, RDF.type, assertive))
    g.add((subj, RDF.type, CIDOC["E5_Event"]))
    g.add((subj, CIDOC["P1_is_identified_by"], Literal("Grigoriou, Dimitra")))
    label = " ".join(x.xpath("./tei:label//text()", namespaces=doc.nsmap))
    g.add((subj, RDFS.label, Literal(label)))
    desc = " ".join(x.xpath("./tei:desc//text()", namespaces=doc.nsmap))
    g.add((subj, RDFS.comment, Literal(desc)))
    # check if there is another event inside and create type
    try:
        na_event = x.xpath("./tei:event", namespaces=doc.nsmap)[0]
    except IndexError:
        na_event = None
    if na_event is not None:
        xml_id = na_event.attrib["{http://www.w3.org/XML/1998/namespace}id"]
        item_id = f"{AMP}{xml_id}"
        subj2 = URIRef(item_id)
        g.add((subj2, RDF.type, CIDOC["E5_Event"]))
        na_event_type = na_event.attrib["type"]
        if na_event_type == "assertive":
            g.add((subj2, RDF.type, assertive))
        elif na_event_type == "non-assertive":
            g.add((subj2, RDF.type, non_assertive))
        else:
            g.add((subj2, RDF.type, assertive))
        # create sub-event properties
        resp = na_event.attrib["resp"]
        cert = na_event.attrib["cert"]
        date_from = na_event.attrib["from"]
        date_to = na_event.attrib["to"]
        label = " ".join(na_event.xpath("./tei:label//text()", namespaces=doc.nsmap))
        desc = " ".join(na_event.xpath("./tei:desc//text()", namespaces=doc.nsmap))
        g.add((subj2, CIDOC["P1_is_identified_by"], Literal("Grigoriou, Dimitra")))
        g.add((subj2, RDFS.label, Literal(label)))
        g.add((subj2, RDFS.comment, Literal(desc)))
        g.add((subj2, CIDOC["P14_carried_out_by"], Literal(resp)))
        g.add((subj2, CIDOC["P82a_begin_of_the_begin"], Literal(date_from)))
        g.add((subj2, CIDOC["P82b_end_of_the_end"], Literal(date_to)))
        g.add((subj2, CIDOC["P81a_end_of_the_begin"], Literal(date_from)))
        g.add((subj2, CIDOC["P81b_begin_of_the_end"], Literal(date_to)))
        idno = na_event.xpath("./tei:idno//text()", namespaces=doc.nsmap)[0]
        idno_uri = URIRef(f"{AMP}{idno.split('https://doi.org/')[-1]}")
        g.add((idno_uri, RDF.type, nano_publication))
        g.add((idno_uri, CIDOC["P70_is_documented_in"], URIRef(idno)))
        g.add((subj2, CIDOC["P9_consists_of"], idno_uri))
        g.add((idno_uri, CIDOC["P123_resulted_from"], subj))
        g.add((subj, CIDOC["P123_resulted_in"], idno_uri))
g_all = ConjunctiveGraph(store=store)
g_all.serialize(destination=os.path.join(rdf_dir, "events.ttl"), format="turtle")
g_all.serialize(destination=os.path.join(rdf_dir, "events.trig"), format="trig")
