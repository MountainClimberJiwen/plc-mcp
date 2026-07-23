using System;
using System.Xml.Linq;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using System.Linq;

public class SclToXmlConverter
{
    private int currentUId = 1;
    
    public XDocument ConvertSclToXml(string sclCode, string blockName, string blockNumber)
    {
        // Create the base XML structure
        var doc = new XDocument(
            new XDeclaration("1.0", "utf-8", null),
            new XElement("Document",
                new XElement("Engineering", new XAttribute("version", "V19")),
                CreateDocumentInfo(),
                CreateFunctionBlock(blockName, blockNumber, sclCode)
            )
        );

        return doc;
    }

    private XElement CreateDocumentInfo()
    {
        return new XElement("DocumentInfo",
            new XElement("Created", DateTime.UtcNow.ToString("o")),
            new XElement("ExportSetting", "WithDefaults"),
            new XElement("InstalledProducts",
                new XElement("Product",
                    new XElement("DisplayName", "Totally Integrated Automation Portal"),
                    new XElement("DisplayVersion", "V19")
                ),
                new XElement("OptionPackage",
                    new XElement("DisplayName", "TIA Portal Openness"),
                    new XElement("DisplayVersion", "V19")
                )
            )
        );
    }

    private XElement CreateFunctionBlock(string blockName, string blockNumber, string sclCode)
    {
        return new XElement("SW.Blocks.FB",
            new XAttribute("ID", "0"),
            new XElement("AttributeList",
                new XElement("AutoNumber", "true"),
                new XElement("HeaderAuthor", ""),
                new XElement("HeaderFamily", ""),
                new XElement("HeaderName", ""),
                new XElement("HeaderVersion", "0.1"),
                CreateInterface(),
                new XElement("MemoryLayout", "Optimized"),
                new XElement("Name", blockName),
                new XElement("Number", blockNumber),
                new XElement("ProgrammingLanguage", "SCL")
            ),
            new XElement("ObjectList",
                CreateCompileUnit(sclCode)
            )
        );
    }

    private XElement CreateInterface()
    {
        return new XElement("Interface",
            new XElement("Sections",
                new XAttribute("xmlns", "http://www.siemens.com/automation/Openness/SW/Interface/v5"),
                CreateInterfaceSection("Input"),
                CreateInterfaceSection("Output"),
                CreateInterfaceSection("InOut"),
                CreateInterfaceSection("Static"),
                CreateInterfaceSection("Temp"),
                CreateInterfaceSection("Constant")
            )
        );
    }

    private XElement CreateInterfaceSection(string sectionName)
    {
        return new XElement("Section",
            new XAttribute("Name", sectionName)
        );
    }

    private XElement CreateCompileUnit(string sclCode)
    {
        return new XElement("SW.Blocks.CompileUnit",
            new XAttribute("ID", "3"),
            new XAttribute("CompositionName", "CompileUnits"),
            new XElement("AttributeList",
                new XElement("NetworkSource",
                    CreateStructuredText(sclCode)
                ),
                new XElement("ProgrammingLanguage", "SCL")
            )
        );
    }

    private XElement CreateStructuredText(string sclCode)
    {
        var structuredText = new XElement("StructuredText",
            new XAttribute("xmlns", "http://www.siemens.com/automation/Openness/SW/NetworkSource/StructuredText/v4"));

        // Parse SCL code and create corresponding XML elements
        var tokens = TokenizeSclCode(sclCode);
        foreach (var token in tokens)
        {
            switch (token.Type)
            {
                case TokenType.Variable:
                    structuredText.Add(CreateAccessElement(token.Value));
                    break;
                case TokenType.Operator:
                    structuredText.Add(CreateTokenElement(token.Value));
                    break;
                case TokenType.Whitespace:
                    structuredText.Add(CreateBlankElement(1));
                    break;
            }
        }

        return structuredText;
    }

    private XElement CreateAccessElement(string variableName)
    {
        return new XElement("Access",
            new XAttribute("Scope", "LocalVariable"),
            new XAttribute("UId", GetNextUId()),
            new XElement("Symbol",
                new XAttribute("UId", GetNextUId()),
                new XElement("Component",
                    new XAttribute("Name", variableName),
                    new XAttribute("UId", GetNextUId())
                )
            )
        );
    }

    private XElement CreateTokenElement(string text)
    {
        return new XElement("Token",
            new XAttribute("Text", text),
            new XAttribute("UId", GetNextUId())
        );
    }

    private XElement CreateBlankElement(int num)
    {
        return new XElement("Blank",
            new XAttribute("Num", num),
            new XAttribute("UId", GetNextUId())
        );
    }

    private int GetNextUId()
    {
        return currentUId++;
    }

    private enum TokenType
    {
        Variable,
        Operator,
        Whitespace
    }

    private class Token
    {
        public TokenType Type { get; set; }
        public string Value { get; set; }
    }

    private List<Token> TokenizeSclCode(string sclCode)
    {
        var tokens = new List<Token>();
        var pattern = @"([a-zA-Z_]\w*|:=|\+|-|\*|/|;|\s+)";
        
        foreach (Match match in Regex.Matches(sclCode, pattern))
        {
            var value = match.Value;
            if (string.IsNullOrWhiteSpace(value))
            {
                tokens.Add(new Token { Type = TokenType.Whitespace, Value = value });
            }
            else if (Regex.IsMatch(value, @"^[a-zA-Z_]\w*$"))
            {
                tokens.Add(new Token { Type = TokenType.Variable, Value = value });
            }
            else
            {
                tokens.Add(new Token { Type = TokenType.Operator, Value = value });
            }
        }
        
        return tokens;
    }
} 

