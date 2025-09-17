package policies.mediacomposer.l4

default allow = false

allow if {
    input.region == "us"
    input.usage == "1 TB"
    input.License == "Avid Platinum"
}
