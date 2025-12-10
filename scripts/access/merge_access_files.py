#!/usr/bin/env python3
import argparse
import sys
import os
from dataclasses import dataclass
from typing import Optional, Set, List

TAB = "\t"    # one tab (four spaces visually)
    
@dataclass(frozen=True)
class AccessEntry:
    access: str          # should include transitive for our use-case
    kind: str            # class, field, method
    owner: str
    name: Optional[str]  # None for class
    desc: Optional[str]  # field desc or method desc, missing for field from access transformer

    def identity_key(self):
        return (self.access, self.kind, self.owner, self.name or "")

    def key(self):
        return (self.owner, self.name or "", self.desc or "", self.access, self.kind)

    def to_line(self):
        if self.kind == "class":
            return TAB.join([self.access, self.kind, self.owner])
        if self.kind == "field":
            return TAB.join([self.access, self.kind, self.owner, self.name, self.desc])
        if self.kind == "method":
            return TAB.join([self.access, self.kind, self.owner, self.name, self.desc])
        
        raise ValueError("invalid kind")
    
def strip_comment(line: str) -> str:
    i = line.find("#")
    if i == -1:
        return line.strip()
    
    return line[:i].strip()

def parse_class_tweaker(path: str) -> Set[AccessEntry]:
    out: Set[AccessEntry] = set()
    with open(path) as lines:
        for raw in lines:
            line = strip_comment(raw)
            if not line or line.startswith("classTweaker") or line.startswith("accessWidener"):
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            access = parts[0]
            kind = parts[1]
            owner = parts[2]

            if kind == "class" and len(parts) == 3:
                out.add(AccessEntry(access, kind, owner, None, None))

            elif kind == "field" and len(parts) == 5:
                name = parts[3]
                desc = parts[4]
                out.add(AccessEntry(access, kind, owner, name, desc))

            elif kind == "method" and len(parts) == 5:
                name = parts[3]
                desc = parts[4]
                out.add(AccessEntry(access, kind, owner, name, desc))

    return out

def parse_access_transformer(path: str) -> Set[AccessEntry]:
    out: Set[AccessEntry] = set()
    with open(path) as lines:
        for raw in lines:
            line = strip_comment(raw)
            if not line:
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            owner = parts[1].replace(".", "/")
            match parts[0]:
                case "public-f":
                    access = ["transitive-accessible", "transitive-mutable"]
                case "public":
                    # Class tweakers make private methods final when made public
                    # There might be another entry that makes them mutable again, so be prepared for that
                    access = ["transitive-accessible", "transitive-mutable"]
                case "protected-f":
                    access = ["transitive-extendable", "transitive-mutable"]
                case "protected":
                    access = ["transitive-extendable"]
                case _:
                    # All other access changes cannot be handled by class tweakers
                    continue

            # class
            if len(parts) == 2:
                for modifier in access:
                    out.add(AccessEntry(modifier, "class", owner, None, None))

                continue

            if len(parts) == 3:

                # method
                if "(" in parts[2]:
                    method = parts[2]
                    name, desc = method.split("(", 1)
                    desc = "(" + desc
                    for modifier in access:
                        out.add(AccessEntry(modifier, "method", owner, name, desc))

                    continue

                # field
                else:
                    name = parts[2]
                    # NeoForge does not include descriptor so it is unknown
                    # Will have to take it from Fabric if there is a matching entry
                    for modifier in access:
                        out.add(AccessEntry(modifier, "field", owner, name, None))

                    continue

    return out

def file_extension(path: str) -> str:
    _, extension = os.path.splitext(path)
    return extension.lower() if extension else None

def collect_entries(paths: List[str]) -> (Set[AccessEntry], Set[AccessEntry]):
    class_tweaker_entries: Set[AccessEntry] = set()
    access_transformer_entries: Set[AccessEntry] = set()
    for path in paths:
        extension = file_extension(path)
        if extension in (".classtweaker", ".accesswidener"):
            class_tweaker_entries |= parse_class_tweaker(path)
        elif extension == ".cfg":
            access_transformer_entries |= parse_access_transformer(path)
        else:
            print(f"Skipping unsupported file: {path}", file=sys.stderr)

    return class_tweaker_entries, access_transformer_entries

def main():
    parser = argparse.ArgumentParser(
        description="Merge Class Tweaker, Access Widener and Access Transformer files."
    )
    # One or more input files
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Input files (.accesswidener, .classtweaker, .cfg)"
    )
    # Output file
    parser.add_argument(
        "output",
        help="Output file (.accesswidener or .classtweaker)"
    )

    args = parser.parse_args()

    input_paths = args.inputs
    output_path = args.output

    class_tweaker_entries, access_transformer_entries = collect_entries(input_paths)
    neo_ids = {entry.identity_key() for entry in access_transformer_entries}

    matches = sorted(
        [entry for entry in class_tweaker_entries if entry.identity_key() in neo_ids],
        key=lambda entry: entry.key()
    )

    extension = file_extension(output_path)
    if extension == ".accesswidener":
        header = ["accessWidener", "v2", "named"]
    else:
        if extension != ".classtweaker":
            print("Warning: output file does not have recognized extension")

        header = ["classTweaker", "v1", "named"]

    # sort by file name, not full path
    sorted_paths = sorted(input_paths, key=os.path.basename)

    # extract base names and join with commas
    names = ", ".join(os.path.basename(f) for f in sorted_paths)

    with open(output_path, "w") as writer:
        writer.write(TAB.join(header).expandtabs(4) + "\n")
        writer.write("# " + names + "\n")
        for entry in matches:
            writer.write(entry.to_line().expandtabs(4) + "\n")

    print(f"written {len(matches)} entries to {output_path}")

if __name__ == "__main__":
    main()
