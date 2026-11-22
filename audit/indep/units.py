"""F4: independent relation units and interface facts (PREREG section 6.1).

Written from SPEC sections 5 and 6 with plain loops. It reads degrees as plain numbers (a Membership is read through its
.value), statuses through their .name, and rows and atoms by attribute. It does not import tesaron.encoder,
tesaron.belnap or tesaron.decoder.
"""

from __future__ import annotations


def _value(x) -> float:
    return float(getattr(x, "value", x))


def _key(atom) -> tuple:
    return (atom.pred, tuple(atom.args))


def relation_units(world, row_ids, vocab_atoms) -> dict:
    """The relation units of the rows `row_ids`: {(pred, args): (mu_pos, mu_neg, provenance)} for every vocabulary atom
    that has at least one report in the rows. mu_pos is the largest support degree of the positive reports (0.0 if there
    is none), mu_neg the same for the negative reports; the provenance is the row ids of all its reports in ascending
    order. The support degree of a source is its reliability in the world (world.source_reliabilities), not the value
    that the encoder's context carries (SPEC section 5, v0 modelling choice of the support degrees)."""
    row_ids = set(row_ids)
    vocab = {_key(a) for a in vocab_atoms}
    pos, neg, ids = {}, {}, {}
    for report in sorted(world.report_rows, key=lambda r: r.row_id):
        key = _key(report.atom)
        if report.row_id not in row_ids or key not in vocab:
            continue
        ids.setdefault(key, []).append(report.row_id)
        target = pos if report.polarity.name == "POS" else neg
        target.setdefault(key, []).append(_value(world.source_reliabilities[report.source]))
    return {
        key: (max(pos.get(key, [0.0])), max(neg.get(key, [0.0])), tuple(ids[key]))
        for key in sorted(ids)
    }


def compare_relation_units(world, row_ids, vocab_atoms, units) -> list:
    """Disagreements between `units` (atom -> unit) and the independent relation units, as strings: a missing or an
    extra unit, a degree that is not exactly equal, a provenance that differs. Relation atoms are those whose predicate
    does not start with "c" (class predicates are c0, c1, ...; relation predicates are r0, r1, ...)."""
    expected = relation_units(world, row_ids, vocab_atoms)
    found = {_key(a): u for a, u in units.items() if not a.pred.startswith("c")}
    problems = []
    for key in sorted(set(expected) | set(found)):
        if key not in found:
            problems.append(f"missing relation unit {key}")
        elif key not in expected:
            problems.append(f"extra relation unit {key}")
        else:
            u = found[key]
            got = (_value(u.mu_pos), _value(u.mu_neg), tuple(u.provenance))
            if got != expected[key]:
                problems.append(f"relation unit {key}: {got} against {expected[key]}")
    return problems


def class_units(world, row_ids, n_classes, usable) -> dict:
    """The class units' provenance and status: {(pred, args): (provenance, status name)}. An entity with at least one
    feature row in `row_ids` has one class unit per class (c0 .. c<n-1>); its provenance is the entity's feature-row ids
    in ascending order; the status is OBSERVED if the PCM fit is usable (converged and not degenerate), else
    NOT_COMPUTED. An entity without such a row has no class units (SPEC section 5 step 5)."""
    row_ids = set(row_ids)
    by_entity = {}
    for row in sorted(world.feature_rows, key=lambda r: r.row_id):
        if row.row_id in row_ids:
            by_entity.setdefault(row.entity, []).append(row.row_id)
    status = "OBSERVED" if usable else "NOT_COMPUTED"
    return {(f"c{k}", (entity,)): (tuple(ids), status) for entity, ids in sorted(by_entity.items())
            for k in range(n_classes)}


def compare_class_units(world, row_ids, n_classes, usable, units) -> list:
    """Disagreements in the class units' presence, provenance and status."""
    expected = class_units(world, row_ids, n_classes, usable)
    found = {_key(a): (tuple(u.provenance), getattr(u.status, "name", str(u.status)))
             for a, u in units.items() if a.pred.startswith("c")}
    problems = []
    for key in sorted(set(expected) | set(found)):
        if key not in found:
            problems.append(f"missing class unit {key}")
        elif key not in expected:
            problems.append(f"extra class unit {key}")
        elif found[key] != expected[key]:
            problems.append(f"class unit {key}: {found[key]} against {expected[key]}")
    return problems


def interface_facts(units, alpha) -> dict:
    """{(channel_name, pred, args): provenance} for all units at threshold alpha, by the Belnap table of SPEC section 6:
    the positive channel holds if mu_pos >= alpha, the negative channel if mu_neg >= alpha (equality counts). A unit
    whose status is NOT_COMPUTED produces no facts."""
    out = {}
    for atom, unit in units.items():
        if getattr(unit.status, "name", str(unit.status)) == "NOT_COMPUTED":
            continue
        key = _key(atom)
        if _value(unit.mu_pos) >= alpha:
            out[("POS", *key)] = tuple(unit.provenance)
        if _value(unit.mu_neg) >= alpha:
            out[("NEG", *key)] = tuple(unit.provenance)
    return out


def compare_interface_facts(units, alpha, facts) -> list:
    """Disagreements between a fact mapping {(channel, atom): provenance} and the independent interface facts."""
    expected = interface_facts(units, alpha)
    found = {(ch.name, *_key(atom)): tuple(prov) for (ch, atom), prov in facts.items()}
    problems = []
    for key in sorted(set(expected) | set(found), key=str):
        if key not in found:
            problems.append(f"alpha={alpha}: missing interface fact {key}")
        elif key not in expected:
            problems.append(f"alpha={alpha}: extra interface fact {key}")
        elif found[key] != expected[key]:
            problems.append(f"alpha={alpha}: provenance of {key} differs")
    return problems
