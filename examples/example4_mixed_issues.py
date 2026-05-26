# Example 4 — Mixed issues: combines style, smells, and performance problems
import json,os,sys

TIMEOUT = 30
MAX_RETRY = 5
BASE_URL = "http://localhost:8000"

user_data = {}
cache = []


class dataProcessor:  # N801: should be DataProcessor
    def __init__(self,source,destination,mode,encoding,chunk_size,validate,transform):  # 7 params
        self.source=source
        self.destination=destination
        self.mode=mode
        self.encoding=encoding
        self.chunk_size=chunk_size
        self.validate=validate
        self.transform=transform

    def ProcessAll(self,records,filters,mappings,output_format,include_meta):  # N802, 5 params
        results=[]
        errors=[]
        skipped=[]
        report=""

        for record in records:
            try:
                if record:
                    if len(record) > 0:
                        if "id" in record:
                            if record["id"] is not None:
                                if filters:
                                    for f in filters:
                                        if f["field"] in record:
                                            if record[f["field"]] == f["value"]:
                                                transformed={}
                                                for key,val in record.items():
                                                    if key in mappings:
                                                        transformed[mappings[key]]=val
                                                    else:
                                                        transformed[key]=val
                                                results.append(transformed)
                                                report += f"Processed: {record['id']}\n"
                                            else:
                                                skipped.append(record["id"])
                                                report += f"Skipped: {record['id']}\n"
                else:
                    errors.append("Empty record")
            except:
                errors.append(f"Error processing record")
                print(f"Failed to process a record")

        print(f"Done: {len(results)} processed, {len(skipped)} skipped, {len(errors)} errors")
        return {"results": results, "errors": errors, "skipped": skipped, "report": report}

    def LoadFromFile(self,path):  # N802
        data=[]
        try:
            with open(path,self.encoding) as f:
                for line in f:
                    line=line.strip()
                    if len(line) > 0:
                        data.append(json.loads(line))
        except:
            pass
        return data

    def SaveToFile(self,data,path):  # N802
        output=""
        for item in data:
            output += json.dumps(item) + "\n"
        with open(path,"w") as f:
            f.write(output)


def buildSummary(data,include_stats,include_errors,max_items,prefix):  # N802
    summary=""
    items=[]
    for d in data:
        if d.get("active"):
            items.append(d["name"])

    if len(items) > 0:
        for i,item in enumerate(items):
            if i < max_items:
                summary += f"{prefix}{item}\n"

    if include_stats:
        count=0
        for item in data:
            count += 1
        summary += f"Total: {count}\n"

    return summary
