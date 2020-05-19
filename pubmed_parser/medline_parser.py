import re
import numpy as np
from itertools import chain
from collections import defaultdict
from pubmed_parser.utils import read_xml, stringify_children, month_or_day_formater

__all__ = [
    'parse_medline_xml',
    'parse_medline_grant_id'
]


def parse_pmid(medline):
    """Parse PMID from article

    Parameters
    ----------
    medline: Element
        The lxml node pointing to a medline document

    Returns
    -------
    pmid: str
        String version of the PubMed ID
    """
    if medline.find('PMID') is not None:
        pmid = medline.find('PMID').text
    else:
        pmid = ''
    return pmid


def parse_mesh_terms(medline):
    """Parse MESH terms from article

    Parameters
    ----------
    medline: Element
        The lxml node pointing to a medline document

    Returns
    -------
    mesh_terms: str
        String of semi-colon spearated MeSH (Medical Subject Headings)
        terms contained in the document.
    """
    if medline.find('MeshHeadingList') is not None:
        mesh = medline.find('MeshHeadingList')
        mesh_terms_list = [
            m.find('DescriptorName').attrib.get('UI', '') +
            ":" +
            m.find('DescriptorName').text for m in mesh.getchildren()
        ]
        mesh_terms = '; '.join(mesh_terms_list)
    else:
        mesh_terms = ''
    return mesh_terms


def parse_publication_types(medline):
    """Parse Publication types from article

    Parameters
    ----------
    medline: Element
        The lxml node pointing to a medline document

    Returns
    -------
    publication_types: str
        String of semi-colon spearated publication types
    """
    publication_types = []
    publication_type_list = medline.find('Article/PublicationTypeList')
    if publication_type_list is not None:
        publication_type_list = publication_type_list.findall('PublicationType')
        for publication_type in publication_type_list:
            publication_types.append(
                publication_type.attrib.get('UI', '') + ':' + (publication_type.text.strip() or '')
            )
    publication_types = '; '.join(publication_types)
    return publication_types


def parse_keywords(medline):
    """Parse keywords from article, separated by ;

    Parameters
    ----------
    medline: Element
        The lxml node pointing to a medline document

    Returns
    -------
    keywords: str
        String of concatenated keywords.
    """
    keyword_list = medline.find('KeywordList')
    keywords = list()
    if keyword_list is not None:
        for k in keyword_list.findall('Keyword'):
            if k.text is not None:
                keywords.append(k.text)
        keywords = '; '.join(keywords)
    else:
        keywords = ''
    return keywords


def parse_chemical_list(medline):
    """Parse chemical list from article

    Parameters
    ----------
    medline: Element
        The lxml node pointing to a medline document

    Returns
    -------
    chemical_list: str
        String of semi-colon spearated chemical list
    """
    chemical_list = []
    chemicals  = medline.find('ChemicalList')
    if chemicals is not None:
        for chemical in chemicals.findall('Chemical'):
            substance_name = chemical.find('NameOfSubstance')
            chemical_list.append(
                substance_name.attrib.get('UI', '') + ':' + (substance_name.text.strip() or '')
            )
    chemical_list = '; '.join(chemical_list)
    return chemical_list


def parse_other_id(medline):
    """Parse OtherID from article, each separated by ;

    Parameters
    ----------
    medline: Element
        The lxml node pointing to a medline document

    Returns
    -------
    other_id: str
        String of semi-colon separated Other IDs found in the document
    """
    pmc = ''
    other_id = list()
    oids = medline.findall('OtherID')
    if oids is not None:
        for oid in oids:
            if 'PMC' in oid.text:
                pmc = oid.text
            else:
                other_id.append(oid.text)
        other_id = '; '.join(other_id)
    else:
        other_id = ''
    return {
        'pmc': pmc,
        'other_id': other_id
    }


def parse_journal_info(medline):
    """Parse MEDLINE journal information

    Parameters
    ----------
    medline: Element
        The lxml node pointing to a medline document

    Returns
    -------
    dict_out: dict
        dictionary with keys including `medline_ta`, `nlm_unique_id`,
        `issn_linking` and `country`

    """
    journal_info = medline.find('MedlineJournalInfo')
    if journal_info is not None:
        if journal_info.find('MedlineTA') is not None:
            medline_ta = journal_info.find('MedlineTA').text or '' # equivalent to Journal name
        else:
            medline_ta = ''
        if journal_info.find('NlmUniqueID') is not None:
            nlm_unique_id = journal_info.find('NlmUniqueID').text or ''
        else:
            nlm_unique_id = ''
        if journal_info.find('ISSNLinking') is not None:
            issn_linking = journal_info.find('ISSNLinking').text
        else:
            issn_linking = ''
        if journal_info.find('Country') is not None:
            country = journal_info.find('Country').text or ''
        else:
            country = ''
    else:
        medline_ta = ''
        nlm_unique_id = ''
        issn_linking = ''
        country = ''
    dict_info = {'medline_ta': medline_ta.strip(),
                 'nlm_unique_id': nlm_unique_id,
                 'issn_linking': issn_linking,
                 'country': country}
    return dict_info


def parse_grant_id(medline):
    """Parse Grant ID and related information from a given MEDLINE tree

    Parameters
    ----------
    medline: Element
        The lxml node pointing to a medline document

    Returns
    -------
    grant_list: list
        List of grants acknowledged in the publications. Each
        entry in the dictionary contains the PubMed ID,
        grant ID, grant acronym, country, and agency.
    """
    article = medline.find('Article')
    pmid = parse_pmid(medline)

    grants = article.find('GrantList')
    grant_list = list()
    if grants is not None:
        grants_list = grants.getchildren()
        for grant in grants_list:
            grant_country = grant.find('Country')
            if grant_country is not None:
                country = grant_country.text
            else:
                country = ''
            grant_agency = grant.find('Agency')
            if grant_agency is not None:
                agency = grant_agency.text
            else:
                agency = ''
            grant_acronym = grant.find('Acronym')
            if grant_acronym is not None:
                acronym = grant_acronym.text
            else:
                acronym = ''
            grant_id = grant.find('GrantID')
            if grant_id is not None:
                gid = grant_id.text
            else:
                gid = ''
            grant_dict = {
                'pmid': pmid,
                'grant_id': gid,
                'grant_acronym': acronym,
                'country': country,
                'agency': agency
            }
            grant_list.append(grant_dict)
    return grant_list


def parse_doi(medline):
    """Parse DOI from a given MEDLINE tree

    Parameters
    ----------
    medline: Element
        The lxml node pointing to a medline document

    Returns
    -------
    doi: str, DOI from a given lxml node
    """
    article = medline.find('Article')
    elocation_ids = article.findall('ELocationID')

    doi = ''
    if len(elocation_ids) > 0:
        for e in elocation_ids:
            doi = e.text.strip() or '' if e.attrib.get('EIdType', '') == 'doi' else ''
    return doi


def date_extractor(journal, year_info_only):
    """Extract PubDate information from an Article in the Medline dataset.

    Parameters
    ----------
    journal: Element
        The 'Journal' field in the Medline dataset
    year_info_only: bool
        if True, this tool will only attempt to extract year information from PubDate.
        if False, an attempt will be made to harvest all available PubDate information.
        If only year and month information is available, this will yield a date of
        the form 'YYYY-MM'. If year, month and day information is available,
        a date of the form 'YYYY-MM-DD' will be returned.

    Returns
    -------
    PubDate: str
        PubDate extracted from an article.
        Note: If year_info_only is False and a month could not be
        extracted this falls back to year automatically.
    """
    day = None
    month = None
    issue = journal.xpath('JournalIssue')[0]
    issue_date = issue.find('PubDate')

    if issue_date.find('Year') is not None:
        year = issue_date.find('Year').text
        if not year_info_only:
            if issue_date.find('Month') is not None:
                month = month_or_day_formater(issue_date.find('Month').text)
                if issue_date.find('Day') is not None:
                    day = month_or_day_formater(issue_date.find('Day').text)
    elif issue_date.find('MedlineDate') is not None:
        year_text = issue_date.find('MedlineDate').text
        year = re.findall(r'\d{4}', year_text)
        if len(year) >= 1:
            year = year[0]
        else:
            year = ""
    else:
        year = ""

    if year_info_only or month is None:
        return year
    else:
        return "-".join(str(x) for x in filter(None, [year, month, day]))


inp_list = [["\u0020","\u00A0","\u180E","\u2000","\u2001","\u2002","\u2003","\u2004","\u2005","\u2006","\u2007",
             "\u2008","\u2009","\u200A","\u200B","\u202F","\u205F","\u3000","\uFEFF"]," "]

def replace_multiple(inp_list,inp_string):
    """inp_list: 1st element is a list of possible unicode and the second its replacement"""

    assert  len(inp_list) == 2
    replacement = inp_list[1]
    for x in inp_list[0]:
        inp_string = inp_string.replace(x,replacement)
    return inp_string

def parse_article_info(medline, year_info_only, nlm_category, subscpt = None, supscpt = None, incl_sections = False):
    """Parse article nodes from Medline dataset

    Parameters
    ----------
    medline: Element
        The lxml node pointing to a medline document
    year_info_only: bool
        see: date_extractor()
    nlm_category: bool
        see: parse_medline_xml()

    Returns
    -------
    article: dict
        Dictionary containing information about the article, including
        `title`, `abstract`, `journal`, `author`, `affiliation`, `pubdate`,
        `pmid`, `other_id`, `mesh_terms`, and `keywords`. The field
        `delete` is always `False` because this function parses
        articles that by definition are not deleted.
    """
    article = medline.find('Article')

    if article.find('ArticleTitle') is not None:
        title = stringify_children(article.find('ArticleTitle'),subscpt,supscpt).strip() or ''
    else:
        title = ''

    title = replace_multiple(inp_list,title)
    title = re.sub(' +', ' ',title.replace("\n", "")).strip()

    if incl_sections:
        category = 'NlmCategory' if nlm_category else 'Label'
    if article.find('Abstract/AbstractText') is not None:
        # parsing structured abstract
        if len(article.findall('Abstract/AbstractText')) > 1:
            abstract_list = list()
            for abstract in article.findall('Abstract/AbstractText'):
                if incl_sections:
                    section = abstract.attrib.get(category, '')
                    if section != 'UNASSIGNED':
                        abstract_list.append('\n')
                        abstract_list.append(abstract.attrib.get(category, ''))
                section_text = stringify_children(abstract,subscpt,supscpt).strip()
                abstract_list.append(section_text)
            abstract = ' '.join(abstract_list).strip()
        else:
            abstract = stringify_children(article.find('Abstract/AbstractText'),subscpt,supscpt).strip() or ''
    elif article.find('Abstract') is not None:
        abstract = stringify_children(article.find('Abstract'),subscpt,supscpt).strip() or ''
    else:
        abstract = ''

    abstract = replace_multiple(inp_list,abstract)
    abstract = re.sub(' +', ' ',abstract.replace("\n", "")).strip()

    if article.find('AuthorList') is not None:
        authors = article.find('AuthorList').getchildren()
        authors_info = list()
        affiliations_info = list()
        for author in authors:
            if author.find('Initials') is not None:
                firstname = author.find('Initials').text or ''
            else:
                firstname = ''
            if author.find('LastName') is not None:
                lastname = author.find('LastName').text or ''
            else:
                lastname = ''
            if author.find('AffiliationInfo/Affiliation') is not None:
                affiliation = author.find('AffiliationInfo/Affiliation').text or ''
            else:
                affiliation = ''
            authors_info.append((firstname + ' ' + lastname).strip())
            affiliations_info.append(affiliation)
        affiliations_info = '\n'.join([a for a in affiliations_info if a is not ''])
        authors_info = '; '.join(authors_info)
    else:
        affiliations_info = ''
        authors_info = ''

    journal = article.find('Journal')
    journal_name = ' '.join(journal.xpath('Title/text()'))
    pubdate = date_extractor(journal, year_info_only)

    pmid = parse_pmid(medline)
    doi = parse_doi(medline)
    mesh_terms = parse_mesh_terms(medline)
    publication_types = parse_publication_types(medline)
    chemical_list = parse_chemical_list(medline)
    keywords = parse_keywords(medline)
    other_id_dict = parse_other_id(medline)
    journal_info_dict = parse_journal_info(medline)
    dict_out = {
        'title': title,
        'abstract': abstract,
        'journal': journal_name,
        'author': authors_info,
        'affiliation': affiliations_info,
        'pubdate': pubdate,
        'pmid': pmid,
        'mesh_terms': mesh_terms,
        'publication_types': publication_types,
        'chemical_list': chemical_list,
        'keywords': keywords,
        'doi': doi,
        'delete': False
    }
    dict_out.update(other_id_dict)
    dict_out.update(journal_info_dict)
    return dict_out


def parse_medline_xml(path, year_info_only=True, nlm_category=False,subscpt=None,supscpt=None):
    """Parse XML file from Medline XML format available at
    ftp://ftp.nlm.nih.gov/nlmdata/.medleasebaseline/gz/

    Parameters
    ----------
    path: str
        The path
    year_info_only: bool
        if True, this tool will only attempt to extract year information from PubDate.
        if False, an attempt will be made to harvest all available PubDate information.
        If only year and month information is available, this will yield a date of
        the form 'YYYY-MM'. If year, month and day information is available,
        a date of the form 'YYYY-MM-DD' will be returned.
        NOTE: the resolution of PubDate information in the Medline(R) database varies
        between articles.
        Defaults to True.
    nlm_category: bool, default False
        if True, this will parse structured abstract where each section if original Label
        if False, this will parse structured abstract where each section will be assigned to
        NLM category of each sections

    Returns
    -------
    article_list: list
        Dictionary containing information about articles in NLM format (see
        `parse_article_info`). Articles that have been deleted will be
        added with no information other than the field `delete` being `True`
    """
    tree = read_xml(path)
    medline_citations = tree.findall('//MedlineCitationSet/MedlineCitation')
    if len(medline_citations) == 0:
        medline_citations = tree.findall('//MedlineCitation')
    article_list = list(map(lambda m: parse_article_info(m, year_info_only, nlm_category,subscpt,supscpt), medline_citations))
    delete_citations = tree.findall('//DeleteCitation/PMID')
    dict_delete = [{
        'title': np.nan,
        'abstract': np.nan,
        'journal': np.nan,
        'author': np.nan,
        'affiliation': np.nan,
        'pubdate': np.nan,
        'pmid': p.text,
        'doi': np.nan,
        'other_id': np.nan,
        'pmc': np.nan,
        'mesh_terms': np.nan,
        'keywords': np.nan,
        'publication_types': np.nan, 
        'chemical_list': np.nan,
        'delete': True,
        'medline_ta': np.nan,
        'nlm_unique_id': np.nan,
        'issn_linking': np.nan,
        'country': np.nan,
    } for p in delete_citations]
    article_list.extend(dict_delete)
    return article_list


def parse_medline_grant_id(path):
    """Parse grant id from Medline XML file

    Parameters
    ----------
    path: str
        The path to the XML with the information

    Returns
    -------
    grant_id_list: list
        List of dictionaries for all files in `path`. Each dictionary
        will have the information returned by `parse_grant_id`
    """
    tree = read_xml(path)
    medline_citations = tree.findall('//MedlineCitationSet/MedlineCitation')
    if len(medline_citations) == 0:
        medline_citations = tree.findall('//MedlineCitation')
    grant_id_list = list(map(parse_grant_id, medline_citations))
    grant_id_list = list(chain(*grant_id_list)) # flatten list
    return grant_id_list