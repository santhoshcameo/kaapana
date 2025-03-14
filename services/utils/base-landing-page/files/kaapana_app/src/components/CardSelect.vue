<template>
  <v-container class="pa-0" fluid style="height: 100%">
    <v-card
        @click="onClick"
        height="100%"
    >
      <!--      padding: 5px; background: red-->
      <v-img
          :src="src"
          aspect-ratio="1"
      >
        <template v-slot:placeholder>
          <v-row
              class="fill-height ma-0"
              align="center"
              justify="center"
          >
            <v-progress-circular
                indeterminate
                color="#0088cc"
            ></v-progress-circular>
          </v-row>
        </template>

        <v-app-bar
            flat
            dense
            color="rgba(0, 0, 0, 0)"
        >
          <Chip :items="[modality]"/>
          <v-spacer></v-spacer>
          <CardMenu
              @removeFromCohort="() => {this.$emit('removeFromCohort')}"
              @deleteFromPlatform="() => {this.$emit('deleteFromPlatform')}"
              :cohort_names="cohort_names"
              :cohort_name="cohort_name"
              :seriesInstanceUID="seriesInstanceUID"
              :studyInstanceUID="studyInstanceUID"
          ></CardMenu>
        </v-app-bar>
      </v-img>
      <v-card-text v-if="config.display_card_text">
        <v-row no-gutters>
          <v-col cols="11">
              <div class="text-truncate">
                {{ seriesDescription }}
              </div>
          </v-col>
          <v-col cols="1">
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-icon
                    small
                    v-bind="attrs"
                    v-on="on"
                >
                  mdi-information
                </v-icon>
              </template>
              <v-data-table
                  :headers="[
                    {text: 'Tag', value: 'name'},
                    {text: 'Value', value: 'value'},
                  ]"
                  :items="tagsData"
                  fixed-header
                  :hide-default-footer="true"
                  :items-per-page=-1
                  dense
              />
            </v-tooltip>
          </v-col>
        </v-row>
        <div v-for="data in config.props">
          <div v-if="data['display']">
            <v-row no-gutters style="font-size: x-small">
              <v-col style="margin-bottom: -5px">
                {{ data['name'] }}
              </v-col>
            </v-row>
            <v-row no-gutters style="font-size: small; padding-top: 0" align="start">
              <v-col>
                <div :class="data['truncate'] ? 'text-truncate' : ''">
                  {{ seriesData[data['key']] || 'N/A' }}
                </div>
              </v-col>
            </v-row>
          </div>
        </div>
        <v-row v-if="tags && config.display_tags" no-gutters>
          <TagChip :items="tags" @deleteTag="(tag) => deleteTag(tag)"/>
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
/* eslint-disable */

import Chip from "./Chip.vue";
import TagChip from "./TagChip.vue";
import CardMenu from "./CardMenu";

import {loadSeriesFromMeta, updateTags} from "@/common/api.service"
import {getDicomTags} from "../common/api.service";


export default {
  name: "CardSelect",
  components: {Chip, TagChip, CardMenu},
  props: {
    cohort_name: {
      type: String,
      default: null
    },
    seriesInstanceUID: {
      type: String,
    },
    studyInstanceUID: {
      type: String,
    },
    selected_tags: {
      type: Array,
      default: []
    },
    cohort_names: {
      type: Array,
      default: []
    }
  },
  data() {
    return {
      src: '',
      seriesData: {},
      seriesDescription: '',
      modality: null,
      tags: [],
      config: {},
      tagsData: [],

      // only required for double-click-event
      clicks: 0,
      timer: null,
    };
  },
  async mounted() {
    const type = JSON.parse(localStorage.getItem("Dataset.structuredGallery")) ? 'structured' : 'unstructured'
    const key = `Dataset.CardSelect.config.${type}`
    if (localStorage.getItem(key)) {
      this.config = JSON.parse(localStorage.getItem(key))
    } else {
      if (type === 'unstructured') {
        this.config = {
          display_card_text: true,
          display_tags: true,
          props: [
            {name: "Patient ID", key: '00100020 PatientID_keyword', display: true, truncate: true},
            {name: 'Study Description', key: '00081030 StudyDescription_keyword', display: true, truncate: true},
            {name: 'Study Date', key: '00080020 StudyDate_date', display: true, truncate: true},
          ]
        }
      } else {
        this.config = {
          display_card_text: true,
          display_tags: true,
          props: [
            {name: "Slice thickness", key: '00180050 SliceThickness_float', display: true, truncate: true}
          ]
        }
      }
      localStorage[key] = JSON.stringify(this.config)
    }

    await this.get_data();
    this.tagsData = await getDicomTags(this.studyInstanceUID, this.seriesInstanceUID)
  },
  watch: {
    // todo: why is this needed?
    async seriesInstanceUID() {
      await this.get_data();
    }
  },
  methods: {
    async get_data() {
      if (this.seriesInstanceUID !== '') {
        const data = await loadSeriesFromMeta(this.seriesInstanceUID)
        if (data !== undefined) {
          this.src = data.src || ''
          this.seriesDescription = data.seriesDescription || ''
          this.modality = data.modality || ''
          this.seriesData = data.seriesData || {}
          this.tags = data.tags || []
        }
      }
    },
    async deleteTag(tag) {
      const request_body = [{
        "series_instance_uid": this.seriesInstanceUID,
        "tags": this.tags,
        "tags2add": [],
        "tags2delete": [tag]
      }]
      updateTags(JSON.stringify(request_body))
          .then(() => this.tags = this.tags.filter((_tag) => _tag !== tag))
    },
    modifyTags() {
      let request_body = []

      if (this.selected_tags.length === 0) {
        this.$notify({
          type: 'hint',
          title: 'No label selected',
          text: 'There was no label selected. First select a label and then click on the respective Item to assign it.',
        })
        return
      }

      const tagsAlreadyExist = this.selected_tags.filter(
          el => this.tags.includes(el)
      ).length === this.selected_tags.length
      if (tagsAlreadyExist) {
        // the selected tags are already included in the tags => removing them
        request_body = [{
          "series_instance_uid": this.seriesInstanceUID,
          "tags": this.tags,
          "tags2add": [],
          "tags2delete": this.selected_tags
        }]
      } else {
        request_body = [{
          "series_instance_uid": this.seriesInstanceUID,
          "tags": this.tags,
          "tags2add": this.selected_tags,
          "tags2delete": []
        }]
      }

      updateTags(JSON.stringify(request_body))
          .then(() => {
            this.tags =
                tagsAlreadyExist
                    ? this.tags.filter(tag => !this.selected_tags.includes(tag))
                    : Array.from(new Set([...this.tags, ...this.selected_tags]))
          })
    },
    onClick() {
      // this.$emit('delete')
      // helper function
      function single_click() {
        this.timer = setTimeout(() => {
          this.clicks = 0;
          // single click
          this.modifyTags()
        }, 300);
      }

      this.clicks++;
      if (this.clicks === 1) {
        return single_click.call(this);
      }

      clearTimeout(this.timer);
      this.clicks = 0;
      // double click
      this.show_details(this.seriesInstanceUID)
      // TODO: add indicator for selected element
    },
    show_details(objectImage) {
      this.$emit('imageId', objectImage);
    }
  }
};
</script>

<style>
.vue-select-image__thumbnail--selected {
  background: #0088cc !important;
}

.vue-select-image__thumbnail--disabled {
  background: #b9b9b9;
  cursor: not-allowed;
}
</style>
