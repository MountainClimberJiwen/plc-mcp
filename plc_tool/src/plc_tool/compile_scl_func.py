name = "block_1"

scl_code = open(f"plc_tool/src/plc_tool/{name}.scl", "r").read()


template = f"""<?xml version="1.0" encoding="utf-8"?>
<Document>
  <Engineering version="V19" />
  <DocumentInfo>
    <Created>2025-04-08T02:44:00.3922635Z</Created>
    <ExportSetting>WithDefaults</ExportSetting>
    <InstalledProducts>
      <Product>
        <DisplayName>Totally Integrated Automation Portal</DisplayName>
        <DisplayVersion>V19</DisplayVersion>
      </Product>
      <OptionPackage>
        <DisplayName>TIA Portal Openness</DisplayName>
        <DisplayVersion>V19</DisplayVersion>
      </OptionPackage>
      <OptionPackage>
        <DisplayName>TIA Portal Version Control Interface</DisplayName>
        <DisplayVersion>V19</DisplayVersion>
      </OptionPackage>
      <Product>
        <DisplayName>STEP 7 Professional</DisplayName>
        <DisplayVersion>V19</DisplayVersion>
      </Product>
      <OptionPackage>
        <DisplayName>STEP 7 Safety</DisplayName>
        <DisplayVersion>V19</DisplayVersion>
      </OptionPackage>
      <Product>
        <DisplayName>WinCC Basic/Comfort/Advanced</DisplayName>
        <DisplayVersion>V19</DisplayVersion>
      </Product>
      <Product>
        <DisplayName>WinCC Unified</DisplayName>
        <DisplayVersion>V19</DisplayVersion>
      </Product>
    </InstalledProducts>
  </DocumentInfo>
  <SW.Blocks.FB ID="0">
    <AttributeList>
      <AutoNumber>true</AutoNumber>
      <HeaderAuthor />
      <HeaderFamily />
      <HeaderName />
      <HeaderVersion>0.1</HeaderVersion>
      <Interface><Sections xmlns="http://www.siemens.com/automation/Openness/SW/Interface/v5">
  <Section Name="Input" />
  <Section Name="Output" />
  <Section Name="InOut" />
  <Section Name="Static" />
  <Section Name="Temp" />
  <Section Name="Constant" />
</Sections></Interface>
      <IsRetainMemResEnabled>false</IsRetainMemResEnabled>
      <MemoryLayout>Optimized</MemoryLayout>
      <MemoryReserve>100</MemoryReserve>
      <Name>{name}</Name>
      <Namespace />
      <Number>1</Number>
      <ProgrammingLanguage>STL</ProgrammingLanguage>
      <UDABlockProperties />
      <UDAEnableTagReadback>false</UDAEnableTagReadback>
    </AttributeList>
    <ObjectList>
      <MultilingualText ID="1" CompositionName="Comment">
        <ObjectList>
          <MultilingualTextItem ID="2" CompositionName="Items">
            <AttributeList>
              <Culture>en-US</Culture>
              <Text>{scl_code}</Text>
            </AttributeList>
          </MultilingualTextItem>
        </ObjectList>
      </MultilingualText>
      <SW.Blocks.CompileUnit ID="3" CompositionName="CompileUnits">
        <AttributeList>
          <NetworkSource><StatementList xmlns="http://www.siemens.com/automation/Openness/SW/NetworkSource/StatementList/v5" /></NetworkSource>
          <ProgrammingLanguage>STL</ProgrammingLanguage>
        </AttributeList>
        <ObjectList>
          <MultilingualText ID="4" CompositionName="Comment">
            <ObjectList>
              <MultilingualTextItem ID="5" CompositionName="Items">
                <AttributeList>
                  <Culture>en-US</Culture>
                  <Text>{scl_code}</Text>
                </AttributeList>
              </MultilingualTextItem>
            </ObjectList>
          </MultilingualText>
          <MultilingualText ID="6" CompositionName="Title">
            <ObjectList>
              <MultilingualTextItem ID="7" CompositionName="Items">
                <AttributeList>
                  <Culture>en-US</Culture>
                  <Text />
                </AttributeList>
              </MultilingualTextItem>
            </ObjectList>
          </MultilingualText>
        </ObjectList>
      </SW.Blocks.CompileUnit>
      <MultilingualText ID="8" CompositionName="Title">
        <ObjectList>
          <MultilingualTextItem ID="9" CompositionName="Items">
            <AttributeList>
              <Culture>en-US</Culture>
              <Text />
            </AttributeList>
          </MultilingualTextItem>
        </ObjectList>
      </MultilingualText>
    </ObjectList>
  </SW.Blocks.FB>
</Document>
"""

project_path = "E:\\TIA_Projects\\test3"
project_name = "SimpleCounter2"
from demo_1 import TiaProject
tia_project = TiaProject(project_path, project_name)
# output template xml path
output_xml_path = "E:\\pycharm-projects\\tia-openness\\exports\\BLOCK_4.xml"
# with open(output_xml_path, "w") as f:
#     f.write(template)

tia_project.update_plc_block(output_xml_path, block_name='block_1')
