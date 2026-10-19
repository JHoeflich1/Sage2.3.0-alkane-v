"""Create molecule catalog PDFs from local curated JSON and ForceBalance targets.

Run with a Python environment containing RDKit and ReportLab. Optimization
conformers are grouped by canonical isomeric SMILES. Each TD record is drawn
separately, using input.sdf atom ordering and metadata.json scan definitions.
"""
import io
import json
import math
from collections import OrderedDict
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'output'
TARGETS = ROOT.parent / '04_fit-forcefield/fb-fit/targets'


def identity(mol):
    mol = Chem.Mol(mol)
    for atom in mol.GetAtoms():
        atom.SetAtomMapNum(0)
    return Chem.MolToSmiles(Chem.RemoveHs(mol), isomericSmiles=True)


def drawing(mol, dihedrals):
    mol = Chem.Mol(mol)
    selected = {i for d in dihedrals for i in d}
    for atom in mol.GetAtoms():
        atom.SetIntProp('original_index', atom.GetIdx())
        atom.SetAtomMapNum(0)
        # Keep any explicit H that participates in the scanned torsion.
        if atom.GetAtomicNum() == 1 and atom.GetIdx() in selected:
            atom.SetIsotope(2)
    mol = Chem.RemoveHs(mol)
    index = {a.GetIntProp('original_index'): a.GetIdx() for a in mol.GetAtoms()}
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() == 1 and atom.GetIntProp('original_index') in selected:
            atom.SetIsotope(0)
    atoms = [index[i] for i in sorted(selected)]
    bonds = []
    for d in dihedrals:
        assert len(d) == 4
        for a, b in zip(d, d[1:]):
            bond = mol.GetBondBetweenAtoms(index[a], index[b])
            assert bond is not None, (a, b)
            bonds.append(bond.GetIdx())
    rdDepictor.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DCairo(1000, 620)
    options = drawer.drawOptions()
    options.useBWAtomPalette()
    options.padding = 0.12
    options.bondLineWidth = 3
    red = (1.0, 0.15, 0.15)
    drawer.DrawMolecule(mol, highlightAtoms=atoms, highlightBonds=sorted(set(bonds)),
                        highlightAtomColors={i: red for i in atoms},
                        highlightBondColors={i: red for i in bonds})
    drawer.FinishDrawing()
    return ImageReader(io.BytesIO(drawer.GetDrawingText()))


def create_pdf(source):
    data = json.loads(source.read_text())
    entries = [e for values in data['entries'].values() for e in values]
    torsion = source.name.startswith('torsion')
    items = []
    if torsion:
        for entry in entries:
            target = TARGETS / f"torsion-{entry['record_id']}"
            mol = Chem.SDMolSupplier(str(target / 'input.sdf'), removeHs=False)[0]
            assert mol is not None
            assert identity(mol) == identity(Chem.MolFromSmiles(entry['cmiles'])), entry['record_id']
            dihedrals = json.loads((target / 'metadata.json').read_text())['dihedrals']
            assert dihedrals
            items.append((mol, dihedrals, entry['inchi_key'], f"QCArchive record: {entry['record_id']}"))
    else:
        groups = OrderedDict()
        for entry in entries:
            mol = Chem.MolFromSmiles(entry['cmiles'])
            assert mol is not None
            key = identity(mol)
            if key not in groups:
                groups[key] = [mol, [], entry['inchi_key'], []]
            groups[key][3].append(entry['record_id'])
        for mol, dihedrals, key, records in groups.values():
            items.append((mol, dihedrals, key, f"{len(records)} optimization record(s); example: {records[0]}"))
    path = source.with_suffix('.pdf')
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setTitle(source.stem + ' - training molecules')
    width, height = A4
    per_page = 6
    pages = math.ceil(len(items) / per_page)
    for page in range(pages):
        pdf.setFont('Helvetica-Bold', 15)
        pdf.drawString(28, height - 32, 'Torsion drive training molecules' if torsion else 'Geometry optimization training molecules')
        pdf.setFont('Helvetica', 9)
        pdf.drawString(28, height - 49, source.name)
        pdf.drawString(28, height - 64, f'{len(entries)} records; {len(items)} structures shown. ' + ('Red: scanned atoms and bonds.' if torsion else 'Repeated conformers grouped by molecule.'))
        for slot, (mol, dihedrals, key, label) in enumerate(items[page*per_page:(page+1)*per_page]):
            row, col = divmod(slot, 2)
            x = 28 + col * ((width - 56) / 2)
            top = height - 86 - row * 237
            pdf.drawImage(drawing(mol, dihedrals), x, top - 171, width=(width-64)/2, height=166, preserveAspectRatio=True, anchor='c')
            pdf.setFont('Helvetica-Bold', 9)
            pdf.drawString(x + 3, top - 181, f'{page*per_page + slot + 1}. {key}')
            pdf.setFont('Helvetica', 8)
            pdf.drawString(x + 3, top - 195, label)
            if torsion:
                indices = '; '.join('-'.join(str(i+1) for i in d) for d in dihedrals)
                pdf.drawString(x + 3, top - 209, f'Scan atoms (SDF, 1-based): {indices}')
        pdf.setFont('Helvetica', 8)
        pdf.drawRightString(width - 28, 20, f'Page {page+1} / {pages}')
        pdf.showPage()
    pdf.save()
    print(f'{path.name}: {len(items)} depictions, {len(entries)} records, {pages} pages', flush=True)


if __name__ == '__main__':
    for source in sorted(OUTPUT.glob('*training-set*.json')):
        create_pdf(source)
